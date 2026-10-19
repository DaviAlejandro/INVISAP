from locust import HttpUser, task, between


class InvilaraUser(HttpUser):
    wait_time = between(1, 3)

    @task
    def index(self):
        self.client.get("/")

    @task(2)
    def login_page(self):
        self.client.get("/login")
