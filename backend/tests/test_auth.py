import datetime
import os
import sys
import unittest
from typing import Any

sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend"))
)
from flask import Flask, jsonify, request
from infrastructure.authentication import AuthenticationSystem


class TestAuthenticationSystem(unittest.TestCase):
    """Comprehensive test suite for the AuthenticationSystem class"""

    def setUp(self) -> Any:
        """Set up test fixtures"""
        self.app = Flask(__name__)
        self.app.config["TESTING"] = True
        self.secret_key = "test-secret-key"
        self.token_expiration = 24
        self.auth = AuthenticationSystem(
            app=self.app,
            secret_key=self.secret_key,
            token_expiration=self.token_expiration,
        )
        self.client = self.app.test_client()
        self.test_username = "testuser"
        self.test_password = "Password123!"

    def test_initialization(self) -> Any:
        """Test that the AuthenticationSystem initializes correctly"""
        self.assertEqual(self.auth.app, self.app)
        self.assertEqual(self.auth.secret_key, self.secret_key)
        self.assertEqual(self.auth.token_expiration, self.token_expiration)
        self.assertEqual(self.auth.users_db, {})

    def test_register_route(self) -> Any:
        """Test the registration route"""
        with self.app.app_context():
            response = self.client.post(
                "/api/auth/register",
                json={"username": self.test_username, "password": self.test_password},
            )
            self.assertEqual(response.status_code, 201)
            self.assertEqual(response.json["message"], "User registered successfully")
            self.assertIn(self.test_username, self.auth.users_db)
            response = self.client.post(
                "/api/auth/register",
                json={"username": self.test_username, "password": "different_password"},
            )
            self.assertEqual(response.status_code, 409)
            self.assertEqual(response.json["message"], "User already exists")
            response = self.client.post(
                "/api/auth/register", json={"password": self.test_password}
            )
            self.assertEqual(response.status_code, 400)
            self.assertEqual(response.json["message"], "Missing username or password")
            response = self.client.post(
                "/api/auth/register", json={"username": "newuser"}
            )
            self.assertEqual(response.status_code, 400)
            self.assertEqual(response.json["message"], "Missing username or password")
            response = self.client.post("/api/auth/register", json={})
            self.assertEqual(response.status_code, 400)
            self.assertEqual(response.json["message"], "Missing username or password")

    def test_login_route(self) -> Any:
        """Test the login route"""
        with self.app.app_context():
            self.client.post(
                "/api/auth/register",
                json={"username": self.test_username, "password": self.test_password},
            )
            response = self.client.post(
                "/api/auth/login",
                json={"username": self.test_username, "password": self.test_password},
            )
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json["message"], "Login successful")
            self.assertIn("token", response.json)
            self.assertEqual(response.json["username"], self.test_username)
            response = self.client.post(
                "/api/auth/login",
                json={"username": self.test_username, "password": "wrong_password"},
            )
            self.assertEqual(response.status_code, 401)
            self.assertEqual(response.json["message"], "Invalid credentials")
            response = self.client.post(
                "/api/auth/login",
                json={"username": "nonexistent_user", "password": self.test_password},
            )
            self.assertEqual(response.status_code, 401)
            self.assertEqual(response.json["message"], "Invalid credentials")
            response = self.client.post(
                "/api/auth/login", json={"password": self.test_password}
            )
            self.assertEqual(response.status_code, 400)
            self.assertEqual(response.json["message"], "Missing username or password")
            response = self.client.post(
                "/api/auth/login", json={"username": self.test_username}
            )
            self.assertEqual(response.status_code, 400)
            self.assertEqual(response.json["message"], "Missing username or password")
            response = self.client.post("/api/auth/login", json={})
            self.assertEqual(response.status_code, 400)
            self.assertEqual(response.json["message"], "Missing username or password")

    def test_token_generation_verification(self) -> Any:
        """Test JWT token generation and verification"""
        token = self.auth.generate_token(self.test_username)
        self.assertIsInstance(token, str)
        username = self.auth.verify_token(token)
        self.assertEqual(username, self.test_username)

    def test_token_required_decorator(self) -> Any:
        """Test the token_required decorator"""
        test_app = Flask("decorator_test")
        test_app.config["TESTING"] = True
        test_auth = AuthenticationSystem(
            app=test_app,
            secret_key=self.secret_key,
            token_expiration=self.token_expiration,
        )
        test_auth.users_db[self.test_username] = {
            "username": self.test_username,
            "password": b"dummy_hashed_password",
            "created_at": datetime.datetime.utcnow(),
        }

        @test_app.route("/api/test_protected")
        @test_auth.token_required
        def protected_route():
            return jsonify(
                {"message": "Access granted", "user": request.user["username"]}
            )

        test_client = test_app.test_client()
        with test_app.app_context():
            token = test_auth.generate_token(self.test_username)
            headers = {"Authorization": f"Bearer {token}"}
            response = test_client.get("/api/test_protected", headers=headers)
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json["message"], "Access granted")
            self.assertEqual(response.json["user"], self.test_username)
            response = test_client.get("/api/test_protected")
            self.assertEqual(response.status_code, 401)
            self.assertEqual(response.json["message"], "Token is missing")
            headers = {"Authorization": "Bearer invalid.token.string"}
            response = test_client.get("/api/test_protected", headers=headers)
            self.assertEqual(response.status_code, 401)
            self.assertIn("Token is invalid", response.json["message"])

    def test_password_hashing(self) -> Any:
        """Test that passwords are properly hashed"""
        with self.app.app_context():
            self.client.post(
                "/api/auth/register",
                json={"username": self.test_username, "password": self.test_password},
            )
            stored_password = self.auth.users_db[self.test_username]["password"]
            self.assertNotEqual(stored_password, self.test_password.encode("utf-8"))
            import bcrypt

            self.assertTrue(
                bcrypt.checkpw(self.test_password.encode("utf-8"), stored_password)
            )

    def test_token_expiration(self) -> Any:
        """Test token expiration"""
        test_app = Flask("expiration_test")
        test_app.config["TESTING"] = True
        short_auth = AuthenticationSystem(
            app=test_app, secret_key=self.secret_key, token_expiration=1 / 3600
        )
        token = short_auth.generate_token(self.test_username)
        username = short_auth.verify_token(token)
        self.assertEqual(username, self.test_username)
        import time

        time.sleep(1.1)
        import jwt

        with self.assertRaises(jwt.ExpiredSignatureError):
            short_auth.verify_token(token)

    def test_security_headers(self) -> Any:
        """Test that security headers are properly set"""
        with self.app.app_context():
            response = self.client.post(
                "/api/auth/register",
                json={"username": self.test_username, "password": self.test_password},
            )
            self.assertEqual(response.content_type, "application/json")


if __name__ == "__main__":
    unittest.main()
