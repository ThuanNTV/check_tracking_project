from flask import Flask, render_template, request, jsonify
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import os

from Util.util import detect_carrier

app = Flask(__name__)


def scrape_spx(tracking_number):
    """
    Lấy thông tin đơn hàng từ Shopee Express.

    Args:
        tracking_number: Mã vận đơn SPX

    Returns:
        dict: Thông tin chi tiết đơn hàng
    """
    try:
        url = f"https://spx.vn/shipment/order/open/order/get_order_info?spx_tn={tracking_number}&language_code=vi"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36'
        }

        response = requests.get(url, headers=headers)
        data = response.json()

        if data['retcode'] != 0:
            return {"error": "Không tìm thấy thông tin đơn hàng"}

        timeline = []
        locations = set()
        current_status = ""
        delivered_time = None

        for event in data['data']['sls_tracking_info']['records']:
            timestamp = datetime.fromtimestamp(event['actual_time']) if event['actual_time'] else None
            formatted_time = timestamp.strftime("%d/%m/%Y %H:%M") if timestamp else "N/A"

            timeline_entry = {
                "datetime": formatted_time,
                "description": event['buyer_description'],
                "status": event['tracking_name'],
                "milestone": event['milestone_name']
            }
            timeline.append(timeline_entry)

            if event['current_location'].get('location_name'):
                loc_info = f"{event['current_location']['location_name']} - {event['current_location']['full_address']}"
                locations.add(loc_info)

            if event['tracking_code'] == 'F980':
                delivered_time = timestamp
                current_status = "✅ ĐÃ GIAO THÀNH CÔNG"
            elif not current_status:
                current_status = event['buyer_description']

        return {
            "carrier": "Shopee Express (SPX)",
            "tracking_number": tracking_number,
            "status": current_status,
            "delivered_time": delivered_time.strftime("%d/%m/%Y %H:%M") if delivered_time else None,
            "timeline": timeline,
            "locations": list(locations),
            "contact_info": []
        }

    except Exception as e:
        return {"error": str(e)}


def scrape_jtexpress(tracking_number, phone=""):
    """
    Lấy thông tin đơn hàng từ J&T Express.

    Args:
        tracking_number: Mã vận đơn J&T
        phone: Số điện thoại người nhận (tùy chọn)

    Returns:
        dict: Thông tin chi tiết đơn hàng
    """
    try:
        url = f"https://jtexpress.vn/vi/tracking?type=track&billcode={tracking_number}&cellphone={phone}"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36'
        }

        response = requests.get(url, headers=headers)
        soup = BeautifulSoup(response.text, 'html.parser')

        # Kiểm tra xem có tìm thấy thông tin đơn hàng không
        result_container = soup.find('div', class_='result-tracking')
        if not result_container or "không tìm thấy" in response.text.lower():
            return {"error": "Không tìm thấy thông tin đơn hàng"}

        # Lấy mã vận đơn hiển thị từ thẻ span trong header
        header_span = soup.find('span', class_='text-grey-darkest')
        displayed_tracking = header_span.text.strip() if header_span else tracking_number

        # Lấy trạng thái tổng quan từ sự kiện mới nhất
        status = "Đang xử lý"
        status_container = soup.find('div', class_='result-vandon-item')
        if status_container:
            description_div = status_container.find('div', recursive=False)
            if description_div:
                status = description_div.get_text(strip=True)

        # Lấy lịch sử chi tiết
        timeline = []
        locations = set()
        delivered_time = None
        contact_info = set()

        for item in soup.find_all('div', class_='result-vandon-item'):
            # Trích xuất thời gian
            time_element = item.find('ion-icon', {'name': 'time-outline'})
            time = time_element.find_next('span').text.strip() if time_element else 'N/A'

            # Trích xuất ngày tháng
            date_element = item.find('ion-icon', {'name': 'calendar-clear-outline'})
            date = date_element.find_next('span').text.strip() if date_element else 'N/A'

            # Định dạng lại ngày tháng theo DD/MM/YYYY
            try:
                date_obj = datetime.strptime(date, "%Y-%m-%d")
                formatted_date = date_obj.strftime("%d/%m/%Y")
            except:
                formatted_date = date

            datetime_str = f"{formatted_date} {time}"

            # Trích xuất mô tả và xử lý các thẻ HTML bên trong
            description_div = item.find_all('div')[-1] if item.find_all('div') else None

            if description_div:
                # Giữ nguyên text và các thẻ font để lấy được text có màu
                description_html = str(description_div)

                # Lấy text sạch để xử lý logic
                description_text = description_div.get_text(strip=True)
                description_text = description_text.replace('\n', ' ').replace('  ', ' ')

                # Trích xuất chi tiết
                # 1. Trích xuất các địa điểm (nằm trong thẻ font color="#1F8DDC")
                font_elements = description_div.find_all('font', color="#1F8DDC")
                for font in font_elements:
                    location_text = font.text.strip()
                    if location_text and not location_text.startswith('+'):  # Bỏ qua số điện thoại
                        locations.add(location_text)

                # 2. Trích xuất thông tin liên hệ (SDT)
                if "SĐT" in description_text or "+" in description_text:
                    phone_matches = [font.text.strip() for font in font_elements
                                     if font.text.strip().startswith('+')]
                    for phone in phone_matches:
                        contact_info.add(phone)

                # 3. Kiểm tra trạng thái giao hàng
                if "đã giao hàng" in description_text.lower() or "giao thành công" in description_text.lower():
                    if not delivered_time:
                        delivered_time = datetime_str
                        status = "✅ ĐÃ GIAO THÀNH CÔNG"
            else:
                description_text = "N/A"
                description_html = "N/A"

            timeline_entry = {
                "datetime": datetime_str,
                "description": description_text,
                "status": "",  # J&T không cung cấp trạng thái riêng
                "milestone": "",  # J&T không cung cấp milestone
                "html_description": description_html  # Lưu mô tả HTML gốc nếu cần
            }
            timeline.append(timeline_entry)

        return {
            "carrier": "J&T Express",
            "tracking_number": displayed_tracking,
            "status": status,
            "delivered_time": delivered_time,
            "timeline": timeline,
            "locations": list(locations),
            "contact_info": list(contact_info) if contact_info else []
        }

    except Exception as e:
        return {"error": str(e)}


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/track', methods=['POST', 'GET'])
def track():
    if request.method == 'POST':
        tracking_number = request.form.get('tracking_number')
        phone = request.form.get('phone', '')
    else:
        tracking_number = request.args.get('number')
        phone = request.args.get('phone', '')

    if not tracking_number:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({"error": "Vui lòng nhập mã vận đơn"}), 400
        else:
            return render_template('index.html', error="Vui lòng nhập mã vận đơn")

    carrier = detect_carrier(tracking_number)

    if carrier == "Shopee Express (SPX)":
        result = scrape_spx(tracking_number)
    elif carrier == "J&T Express":
        result = scrape_jtexpress(tracking_number, phone)
    else:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({"error": f"Không hỗ trợ đơn vị vận chuyển của mã {tracking_number}"}), 400
        else:
            return render_template('index.html', error=f"Không hỗ trợ đơn vị vận chuyển của mã {tracking_number}")

    if 'error' in result:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify(result), 404
        else:
            return render_template('index.html', error=result['error'])

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify(result)
    else:
        return render_template('result.html', data=result)


if __name__ == '__main__':
    # Tạo thư mục templates nếu chưa tồn tại
    if not os.path.exists('templates'):
        os.makedirs('templates')

    app.run(debug=True)