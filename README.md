# ManuGPT: rewrite your manuscript using OpenAI GPT model

## About ManuGPT

- Template: bootstrap + sb-admin template + font-awesome
- Framework: python3 + flask
- Use OpenAI's [Completions](https://platform.openai.com/docs/api-reference/completions) / [Edits](https://platform.openai.com/docs/api-reference/edits) API to rewrite your paragraph.
- The prompts for paragraph revision is inspired by https://github.com/manubot/manubot-ai-editor

## Installation

### Prerequisites

- Python 3.x (Tested on Python 3.9.10)
- Get your own OpenAI API key from https://platform.openai.com/account/api-keys
- A http proxy is required if you're in countries that can not access OpenAI API directly.

### Clone the repository

```bash
git clone https://github.com/Kevinzjy/ManuGPT.git
cd ManuGPT
```

### Install requirements

```bash
virtual venv
source ./venv/bin/activate
pip install -r requirements.txt
```

### Configuration

Create the file `~/.openai_key` and save your OpenAI key in it. This is optional because you can also input the API key in the web page.

Replace the following configurations in `app.py`

```python3
# ============== CONFIG =====================

# IP of flask app host:
# 127.0.0.1 will only allow local access from your current machine
# 0.0.0.0 will allow remote access from local network
FLASK_HOST = "0.0.0.0"

# Port of flask app:
# Change it to anything you like (should be larger than 1024)
FLASK_PORT = 47118

# Replace your HTTP proxy host and port here
# The OpenAI API requires HTTP proxy for access in mainland china
HTTP_PROXY_HOST = "127.0.0.1"
HTTP_PROXY_PORT = "1087"

# Set PROXIES to None if you do not need proxy to access openAI
# PROXIES = None
PROXIES = {
    "http": f"http://{HTTP_PROXY_HOST}:{HTTP_PROXY_PORT}",
    "https": f"http://{HTTP_PROXY_HOST}:{HTTP_PROXY_PORT}",
}

# Directory for storing temporary files
TMP_DIR = Path("/tmp")

# ============== CONFIG =====================
```

### Run ManuGPT

```bash
python app.py
```

The ip address will be displayed on your screen if everything works fine.

```bash
 * Serving Flask app 'app'
 * Debug mode: off
WARNING: This is a development server. Do not use it in a production deployment. Use a production WSGI server instead.
 * Running on all addresses (0.0.0.0)
 * Running on http://127.0.0.1:47118
 * Running on http://192.168.50.40:47118
```

## Usage

![image](https://github.com/Kevinzjy/ManuGPT/blob/master/screenshot.png)

1. Input the title / keywords of your manuscript. Select which section (Abstract / Introduction / Results / Discussion / Methods ) your paragraph belongs to.
2. Select model from text completion(`text-davinci-003`), text edit (`text-davinci-edit-001`) or chat completion (`gpt-3.5-turbo`). The `text-davinci-003` model is recommended.
3. Make sure the API key is correct. Otherwise, change it in `app.py` or edit in the webpage.
4. Input your paragraph in the left side.
5. Press the "Submit" button in the upper right. Wait patiently for the response. The revised text will be displayed in the right side.
6. Edit the revised paragraph until you're satisfied.
7. Press the "Download" button to download the docx file containing the raw paragraph and tracked changes.

