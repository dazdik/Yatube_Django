import shutil
import tempfile

from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, override_settings, TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from http import HTTPStatus

from posts.models import Comment, Group, Post

User = get_user_model()

TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class PostFormTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='Author')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test-slug',
            description='Тестовое описание'
        )
        cls.small_gif = (
            b'\x47\x49\x46\x38\x39\x61\x02\x00'
            b'\x01\x00\x80\x00\x00\x00\x00\x00'
            b'\xFF\xFF\xFF\x21\xF9\x04\x00\x00'
            b'\x00\x00\x00\x2C\x00\x00\x00\x00'
            b'\x02\x00\x01\x00\x00\x02\x02\x0C'
            b'\x0A\x00\x3B'
        )
        cls.uploaded = SimpleUploadedFile(
            name='small.gif',
            content=cls.small_gif,
            content_type='image/gif'
        )
        cls.post = Post.objects.create(
            author=cls.user,
            text='Тестовый текст',
            group=cls.group,
        )
        cls.form_data = {
            'text': 'New post',
            'group': cls.group.id,
            'image': cls.uploaded
        }
        cls.comment = Comment.objects.create(
            text='Текст комментария',
            post=cls.post,
            author=cls.user
        )

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        """
        Метод shutil.rmtree удаляет директорию и всё её содержимое
        """

        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        # Создаем неавторизованный клиент
        self.authorized_client = Client()
        self.authorized_client.force_login(PostFormTests.user)
        self.guest_client = Client()

    def test_create_post(self):
        """
        Проверка: при отправке формы на создание
        поста создается новая запись в БД
        """

        post_count = Post.objects.count()
        response = self.authorized_client.post(
            reverse('posts:post_create'),
            data=PostFormTests.form_data,
            follow=True
        )
        post = Post.objects.all()[0]
        self.assertRedirects(response,
                             reverse('posts:profile',
                                     kwargs={
                                         'username':
                                         PostFormTests.user.username
                                     }))
        self.assertEqual(Post.objects.count(), post_count + 1)
        self.assertEqual(post.text, PostFormTests.form_data['text'])
        self.assertEqual(post.group.id, PostFormTests.form_data['group'])
        self.assertEqual(post.image.name, 'posts/small.gif')

    def test_edit_form_works_correct(self):
        """
        Форма редактирования поста работает корректно,
        происходит изменение поста с post_id в базе данных.
        """

        post_count = Post.objects.count()
        self.group2 = Group.objects.create(title='Тестовая группа2',
                                           slug='test-group',
                                           description='Описание')
        form_data = {
            'text': 'New edited post',
            'group': self.group2.id,
        }
        response = self.authorized_client.post(
            reverse('posts:post_edit', kwargs={
                'post_id': PostFormTests.post.id
            }),
            data=form_data,
            follow=True
        )
        post = Post.objects.all()[0]
        self.assertRedirects(response,
                             reverse('posts:post_detail',
                                     kwargs={'post_id': post.id}))
        self.assertEqual(Post.objects.count(), post_count)
        self.assertEqual(post.text, form_data['text'])
        self.assertEqual(post.group.id, form_data['group'])

    def test_guest_client_create_post(self):
        """Гость перенаправляется на страницу авторизации"""
        post_id = PostFormTests.post.id
        form_data = {
            'text': 'Guest post',
        }
        response = self.guest_client.post(
            reverse('posts:post_edit', kwargs={
                'post_id': post_id
            }),
            data=form_data,
            follow=True)
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertRedirects(response,
                             f'/auth/login/?next=/posts/{post_id}/edit/')

    def test_comment_form(self):
        """Пользователь может комментировать посты"""

        comments_count = Comment.objects.count()
        form_data = {
            'text': 'Текст комментария',
            'post': PostFormTests.post,
            'author': PostFormTests.user
        }
        post_id = PostFormTests.post.id
        response = self.authorized_client.post(
            reverse('posts:add_comment', kwargs={
                'post_id': post_id
            }),
            data=form_data,
            follow=True
        )
        self.assertEqual(Comment.objects.count(), comments_count + 1)
        add_comment = Comment.objects.first()
        self.assertEqual(add_comment.text, form_data['text'])
        self.assertRedirects(response, reverse(
            'posts:post_detail', kwargs={
                'post_id': post_id
            }
        ))

    def test_guest_not_create_comment(self):
        """Гость не может оставить комментарий к посту."""
        comments_count = Comment.objects.count()
        form_data = {
            'text': 'Текст комментария не существует',
            'post': PostFormTests.post,
        }
        post_id = PostFormTests.post.id
        response = self.guest_client.post(
            reverse('posts:add_comment', kwargs={
                'post_id': post_id
            }),
            data=form_data,
            follow=True
        )
        self.assertEqual(Comment.objects.count(), comments_count)
        self.assertRedirects(
            response, f'/auth/login/?next=/posts/{post_id}/comment/'
        )
