from locust import HttpUser, task, between

class WebsiteUser(HttpUser):
    wait_time = between(1, 3)  
    @task
    def test_homepage(self):
        self.client.get("/")  

    # @task(2)
    # def test_login(self):
    #     self.client.post("/login/", data={"username": "testuser", "password": "testpass"})  # تست لاگین

    @task(3)
    def test_api(self):
        self.client.get("getallProduct/")

