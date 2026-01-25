# import os, requests
# from dotenv import load_dotenv

# load_dotenv()
# url = os.getenv("LOGIC_APP_URL")
# print("URL:", url)

# r = requests.post(url, json={
#     "to": "kshitijphotos1@gmail.com",
#     "subject": "Hello",
#     "body": "This is a test email WITHOUT attachment."
# })

# print(r.status_code, r.text)


# script to checkconnectivity

# import sys
# import socket

# print(f"Current Python Version: {sys.version}")
# print(f"Executable Path: {sys.executable}")

# try:
#     # Try to resolve Google first (to see if it's just Azure or ALL networking)
#     ip = socket.gethostbyname("google.com")
#     print(f"SUCCESS: Resolved google.com to {ip}")
    
#     # Try your Azure endpoint
#     azure_host = "newmedicalocr.cognitiveservices.azure.com"
#     ip_azure = socket.gethostbyname(azure_host)
#     print(f"SUCCESS: Resolved Azure to {ip_azure}")
    
# except Exception as e:
#     print(f"FAILURE: {e}")

import gradio as gr
# Print the installed version of Gradio
print(gr.__version__)