from django.test import TestCase
from http import HTTPStatus


class ViewTestClass(TestCase):
    def test_error_page(self):
        """
        Проверка статуса и использование правильного
        шаблона для страницы с 404 ошибкой
        """
        response = self.client.get('/nonexist-page/')
        self.assertEqual(
            response.status_code,
            HTTPStatus.NOT_FOUND
        )
        self.assertTemplateUsed(response, 'core/404.html')
