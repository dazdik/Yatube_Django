from django.contrib.auth import get_user_model
from django.test import TestCase, Client
from http import HTTPStatus

from posts.models import Follow, Group, Post, User

User = get_user_model()


class PostURLTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='Author')
        cls.user_no_author = User.objects.create_user(username='User')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test-slug',
            description='Тестовое описание'
        )
        cls.post = Post.objects.create(
            author=cls.user,
            text='Тестовый текст',
            group=cls.group
        )

    def setUp(self):
        self.guest_client = Client()
        self.authorized_client = Client()
        self.user_no_author = Client()
        self.authorized_client.force_login(PostURLTests.user)
        self.user_no_author.force_login(PostURLTests.user_no_author)

    def test_urls_available_for_guest(self):
        """Проверка страниц, доступных для неавторизованных пользователей."""

        tests_urls = {
            '/': HTTPStatus.OK,
            f'/group/{PostURLTests.group.slug}/': HTTPStatus.OK,
            f'/profile/{PostURLTests.post.author}/': HTTPStatus.OK,
            f'/posts/{PostURLTests.post.id}/': HTTPStatus.OK,
        }
        for url, status in tests_urls.items():
            with self.subTest(status=status):
                response = self.guest_client.get(url)
                self.assertEqual(
                    response.status_code,
                    status,
                    f'Ошибка доступа для страницы {url} без авторизации.'
                )

    def test_urls_available_for_authorized_client(self):
        """Проверка страниц, доступных для авторизованных пользователей."""

        tests_urls = {
            '/': HTTPStatus.OK,
            f'/group/{PostURLTests.group.slug}/': HTTPStatus.OK,
            f'/profile/{PostURLTests.post.author}/': HTTPStatus.OK,
            f'/posts/{PostURLTests.post.pk}/': HTTPStatus.OK,
            f'/posts/{PostURLTests.post.pk}/edit/': HTTPStatus.OK,
            '/create/': HTTPStatus.OK,
            '/follow/': HTTPStatus.OK,
        }
        for url, status in tests_urls.items():
            with self.subTest(status=status):
                response = self.authorized_client.get(url)
                self.assertEqual(
                    response.status_code,
                    status,
                    f'Ошибка доступа для страницы {url} с авторизацией.'
                )

    # Проверяем редиректы для неавторизованного пользователя
    def test_post_edit_url_redirect_anonymous(self):
        """
        Страница posts/<int:post_id>/edit/ и /create/
        перенаправляет анонимного пользователя.
        """

        urls_redirects = {
            f'/posts/{PostURLTests.post.pk}/edit/':
                f'/auth/login/?next=/posts/{PostURLTests.post.pk}/edit/',
            '/create/': '/auth/login/?next=/create/',
        }
        for url, redirect in urls_redirects.items():
            with self.subTest(url=url):
                response = self.guest_client.get(url, follow=True)
                self.assertRedirects(response, redirect)

    def test_post_edit_redirect_not_author_to_post_detail(self):
        """Страница /posts/<int:post_id>/edit/ доступна только автору поста."""

        response = self.user_no_author.get(
            f'/posts/{PostURLTests.post.pk}/edit/', follow=True
        )
        self.assertRedirects(response, f'/posts/{PostURLTests.post.pk}/')

    def test_urls_uses_correct_template(self):
        """URL-адрес использует соответствующий шаблон."""

        templates_url_names = {
            '/': 'posts/index.html',
            f'/group/{PostURLTests.group.slug}/': 'posts/group_list.html',
            '/create/': 'posts/create_post.html',
            f'/posts/{PostURLTests.post.pk}/': 'posts/post_detail.html',
            f'/posts/{PostURLTests.post.pk}/edit/': 'posts/create_post.html',
            f'/profile/{PostURLTests.post.author}/': 'posts/profile.html',
        }
        for url, template in templates_url_names.items():
            with self.subTest(url=url):
                response = self.authorized_client.get(url)
                self.assertTemplateUsed(response, template)
                self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_profile_follow(self):
        """
        Подписка доступна
        только авторизованным пользователям
        """
        username = PostURLTests.user.username
        response = self.user_no_author.get(f'/profile/{username}/follow/')
        self.assertEqual(response.status_code, HTTPStatus.FOUND)

    def test_profile_unfollow(self):
        """
        Отписка доступна
        только авторизованным пользователям
        """
        Follow.objects.create(
            author=PostURLTests.user,
            user=PostURLTests.user_no_author
        )
        username = PostURLTests.user.username
        response = self.user_no_author.get(f'/profile/{username}/unfollow/')
        self.assertEqual(response.status_code, HTTPStatus.FOUND)

    def test_404_page(self):
        """страница 404 отдаёт кастомный шаблон"""
        url = '/unexisting_page/'
        clients = (
            self.authorized_client,
            self.user_no_author,
            self.guest_client,
        )
        for client in clients:
            with self.subTest(url=url):
                response = client.get(url, follow=True)
                self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)
                self.assertTemplateUsed(response, 'core/404.html')
