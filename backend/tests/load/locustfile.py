"""
Locust load test script for MindFlow Tutor API.
Simulates concurrent students asking questions, uploading frames, and querying documents.
Usage:
    locust -f backend/tests/load/locustfile.py --headless -u 20 -r 5 --run-time 1m --host http://localhost:8000
"""
import base64
import uuid
from locust import HttpUser, task, between


class StudentUser(HttpUser):
    wait_time = between(1.0, 3.0)

    def on_start(self):
        self.session_id = str(uuid.uuid4())
        self.headers = {"Authorization": "Bearer test-load-token"}
        # 1x1 dummy jpeg image
        self.sample_frame_b64 = base64.b64encode(b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x01\x00H\x00H\x00\x00\xff\xdb").decode()

    @task(3)
    def ask_direct_question(self):
        payload = {
            "question": "Can you explain the main difference between velocity and speed?",
            "session_id": self.session_id,
        }
        self.client.post("/api/v1/ask", json=payload, headers=self.headers, name="/v1/ask")

    @task(5)
    def send_detector_frame(self):
        payload = {
            "image_base64": self.sample_frame_b64,
            "session_id": self.session_id,
        }
        self.client.post("/api/v1/detector/frame", json=payload, headers=self.headers, name="/v1/detector/frame")

    @task(2)
    def get_document_list(self):
        self.client.get("/api/v1/documents", headers=self.headers, name="/v1/documents")

    @task(1)
    def check_health(self):
        self.client.get("/api/health", name="/health")
