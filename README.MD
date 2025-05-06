# GitHub Actions Setup for Flask Tracking Application

To run your Flask tracking application on GitHub Actions, you need to set up your repository structure properly. Here's how to organize your files:

## Project Structure

```
your-repository/
├── .github/
│   └── workflows/
│       └── python-flask-app.yml
├── Util/
│   └── util.py
├── templates/
│   ├── index.html
│   └── result.html
├── main.py
├── requirements.txt (recommended)
└── README.md (optional)
```

## Setup Steps

1. **Create the GitHub Actions workflow file**:
   - Create the directory `.github/workflows/` in your repository
   - Add the `python-flask-app.yml` file to this directory

2. **Make sure you have the Util directory with util.py file**:
   - This should contain your carrier detection function
   - The workflow will create a basic version if it doesn't exist

3. **Create the templates directory with required HTML files**:
   - `index.html` for the search form
   - `result.html` for displaying tracking results

4. **Create a requirements.txt file** (recommended):
   ```
   flask==2.3.3
   requests==2.31.0
   beautifulsoup4==4.12.2
   ```

5. **Add your main.py file** (from the provided code)

## Important Notes

- The workflow assumes your main file is named `main.py`
- It creates minimal templates if they don't exist to pass basic testing
- If your app requires specific environment variables, add them as GitHub Secrets
- The workflow doesn't include actual service testing as it would require real tracking numbers