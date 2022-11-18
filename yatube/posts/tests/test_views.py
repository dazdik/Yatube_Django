import shutil
import tempfile

from django import forms
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, override_settings, TestCase
from django.urls import reverse

from ..forms import PostForm
from ..models import Follow, Group, Post, User

User = get_user_model()

TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class PostViewsTests(TestCase):
    """Проверка вью функций приложения Posts"""

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
            image=cls.uploaded
        )

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        """
        Метод shutil.rmtree удаляет директорию и всё её содержимое
        """

        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        self.guest_client = Client()
        self.authorized_client = Client()
        self.user_no_author = Client()
        self.authorized_client.force_login(PostViewsTests.user)
        self.user_no_author.force_login(PostViewsTests.user_no_author)

    def test_pages_uses_correct_template(self):
        """URL-адрес использует соответствующий шаблон"""

        templates_pages_names = {
            reverse('posts:index'): 'posts/index.html',
            reverse('posts:group_list', kwargs={
                'slug': PostViewsTests.group.slug},): 'posts/group_list.html',
            reverse('posts:profile', kwargs={
                'username': PostViewsTests.user}): 'posts/profile.html',
            reverse('posts:post_detail', kwargs={'post_id':
                    PostViewsTests.post.pk}): 'posts/post_detail.html',
            reverse('posts:post_create'): 'posts/create_post.html',
            reverse('posts:post_edit', kwargs={'post_id':
                    PostViewsTests.post.pk}): 'posts/create_post.html',
        }
        # view-классы используют ожидаемые HTML-шаблоны
        for reverse_name, template in templates_pages_names.items():
            with self.subTest(reverse_name=reverse_name):
                response = self.authorized_client.get(reverse_name)
                self.assertTemplateUsed(response, template)

    def test_create_and_edit_show_correct_context(self):
        """Шаблон post_create сформирован с правильным контекстом"""

        response = self.authorized_client.get(reverse('posts:post_create'))
        form = response.context.get('form')
        if response.context.get('is_edit') is True:
            response = self.authorized_author.get(
                reverse('posts:post_edit',
                        kwargs={'post_id': PostViewsTests.post.pk})
            )
        form_fields = {
            'text': forms.fields.CharField,
            'group': forms.fields.ChoiceField,
            'image': forms.fields.ImageField,
        }
        for value, expected in form_fields.items():
            form_field = response.context.get('form').fields.get(value)
            self.assertIsInstance(form_field, expected)
        self.assertIsInstance(form, PostForm)

    def test_post_detail_page_show_correct_context(self):
        """Шаблон post_detail сформирован с правильным контекстом"""

        response = self.authorized_client.get(
            reverse('posts:post_detail', kwargs={
                'post_id': PostViewsTests.post.pk
            }))
        post_text_0 = {
            response.context['post'].text: 'Тестовый пост',
            response.context['post'].group: PostViewsTests.group,
            response.context['post'].author:
            PostViewsTests.user.username,
            response.context['post'].image:
            PostViewsTests.post.image
        }
        for value, expected in post_text_0.items():
            self.assertEqual(post_text_0[value], expected)

    def get_context_for_pages_with_paginator(self, page):
        """Получаем нужный для страниц с паджинатором контекст"""

        pages_reverses = {
            'index': reverse('posts:index'),
            'group_list': reverse('posts:group_list',
                                  kwargs={'slug': PostViewsTests.group.slug}),
            'profile': reverse('posts:profile',
                               kwargs={'username': PostViewsTests.user})
        }
        response = self.authorized_client.get(pages_reverses[page])
        return response.context['page_obj'][0]

    def test_pages_with_pagin_show_correct_context(self):
        """Шаблоны index, profile, group_list сформированы
        с правильным контекстом."""

        for page in ['index', 'group_list', 'profile']:
            post = self.get_context_for_pages_with_paginator(page)
            self.assertEqual(post, PostViewsTests.post)
            if page == 'group_list':
                self.assertEqual(post.group, PostViewsTests.group)

    def test_group_posts_show_correct_context(self):
        """
        Проверяем, что словарь context страницы group_list
        содержит ожидаемые значения
        """
        response = self.authorized_client.get(
            reverse('posts:group_list', kwargs={
                'slug': PostViewsTests.group.slug},)
        )
        group_from_context = response.context['group']
        self.assertEqual(group_from_context, PostViewsTests.group)

    def test_profile_show_correct_context(self):
        """Проверяем, что словарь context страницы profile
        содержит ожидаемые значения """
        response = self.authorized_client.get(
            reverse('posts:profile', kwargs={
                'username': PostViewsTests.user})
        )
        self.assertEqual(response.context['author'], PostViewsTests.user)

    def test_group_shows_new_post_on_pages(self):
        """Пост при создании добавлен корректно"""

        user = User.objects.create_user(username='new_author')
        group = Group.objects.create(title='new_group', slug='new-slug')
        post = Post.objects.create(
            author=user,
            text='новый пост',
            group=group,
        )
        pages = (
            reverse('posts:index'),
            reverse('posts:group_list', kwargs={'slug': group.slug}),
            reverse('posts:profile', kwargs={'username': user.username}),
        )
        for reverses in pages:
            with self.subTest(value=reverses):
                response = self.authorized_client.get(reverses)
                self.assertEqual(
                    response.context.get('page_obj').object_list[0],
                    post,
                )

    def test_post_dont_shows_at_another_pages(self):
        """Пост не попал в группу, для которой не был предназначен"""

        user = User.objects.create_user(username='new_author')
        group = Group.objects.create(title='new_group', slug='new-slug')
        post = Post.objects.create(
            author=user,
            text='новый пост',
            group=group,
        )
        pages = (
            reverse('posts:group_list', kwargs={'slug': self.group.slug}),
            reverse('posts:profile', kwargs={'username': self.user.username}),
        )
        for reverses in pages:
            with self.subTest(value=reverses):
                response = self.authorized_client.get(reverses)
                self.assertNotIn(
                    post,
                    response.context.get('page_obj').object_list,
                )

    def test_index_page_cache(self):
        """Проверка работы кэша для Главной"""
        response = self.authorized_client.get(reverse('posts:index'))
        posts = response.content
        Post.objects.create(
            author=PostViewsTests.user,
            text='новый пост'
        )
        response_2 = self.authorized_client.get(reverse('posts:index'))
        old_posts = response_2.content
        self.assertEqual(old_posts, posts)
        cache.clear()
        response_3 = self.authorized_client.get(reverse('posts:index'))
        new_posts = response_3.content
        self.assertNotEqual(new_posts, old_posts)


NUM_OF_POSTS = 13
POSTS_LIMIT = 10
SECOND_PAGE_NUM_POST = 3


class PaginatorViewsTest(TestCase):
    """Тестирование паджинатора"""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.author = User.objects.create_user(username='Author')
        cls.authorized_author = Client()
        cls.authorized_author.force_login(cls.author)

    def setUp(self):
        self.group = Group.objects.create(
            title='Тестовая группа',
            description='Тестовое описание',
            slug='test-slug',
        )
        self.post = Post.objects.bulk_create([
            Post(author=self.author,
                 text=f'Тестовый пост {i}',
                 group=self.group) for i in range(NUM_OF_POSTS)]
        )
        self.page_names_records = {
            'posts:index': '',
            'posts:profile': {'username': PaginatorViewsTest.author.username},
            'posts:group_list': {'slug': self.group.slug},
        }

    def test_first_page_contains_ten_records(self):
        for page_name, kwarg in self.page_names_records.items():
            with self.subTest(page_name=page_name):
                response = self.client.get(reverse(page_name, kwargs=kwarg))
                self.assertEqual(
                    len(response.context['page_obj']),
                    POSTS_LIMIT
                )

    def test_second_page_contains_three_records(self):
        for page_name, kwarg in self.page_names_records.items():
            with self.subTest(page_name=page_name):
                response = self.client.get(reverse(page_name,
                                                   kwargs=kwarg) + '?page=2')
                self.assertEqual(
                    len(response.context['page_obj']),
                    SECOND_PAGE_NUM_POST
                )


class FollowTests(TestCase):
    """Проверка вью функций сервиса подписок"""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='follower')
        cls.author = User.objects.create_user(username='author')

    def setUp(self):
        self.author_client = Client()
        self.author_client.force_login(FollowTests.author)
        self.user_client = Client()
        self.user_client.force_login(FollowTests.user)
        self.guest_client = Client()

    def test_auth_can_follow(self):
        """
        Авторизованный пользователь может
        подписываться на других пользователей
        """
        count_follow = Follow.objects.count()
        self.user_client.get(
            reverse('posts:profile_follow', kwargs={
                'username': FollowTests.author.username
            })
        )
        self.assertEqual(Follow.objects.count(), count_follow + 1)
        follow_obj = Follow.objects.first()
        self.assertEqual(follow_obj.author, FollowTests.author)
        self.assertEqual(follow_obj.user, FollowTests.user)

    def test_auth_can_unfollow(self):
        """
        Авторизованный пользователь может
        отписываться от других пользователей
        """

        Follow.objects.create(
            author=FollowTests.author,
            user=FollowTests.user
        )
        count_follow = Follow.objects.count()
        self.user_client.get(
            reverse('posts:profile_unfollow', kwargs={
                'username': FollowTests.author.username
            })
        )
        self.assertEqual(Follow.objects.count(), count_follow - 1)

    def test_unauth_user_can_not_follow(self):
        """Гость не может подписаться на авторов"""

        count_follow = Follow.objects.count()
        response = self.guest_client.get(
            reverse('posts:profile_follow', kwargs={
                'username': FollowTests.author.username
            })
        )
        first_redirect = reverse('users:login')
        next_redirect = reverse('posts:profile_follow', kwargs={
            'username': FollowTests.author.username
        })
        self.assertEqual(Follow.objects.count(), count_follow)
        self.assertRedirects(
            response, first_redirect + f'?next={next_redirect}'
        )

    def test_follow_index_contains_new_posts(self):
        """
        Новая запись автора появляется в ленте тех,
        кто на него подписан
        """

        Follow.objects.create(
            author=FollowTests.author,
            user=FollowTests.user
        )
        new_post = Post.objects.create(
            text='Текст для проверки подписки',
            author=FollowTests.author
        )
        response = self.user_client.get(reverse(
            'posts:follow_index'
        ))
        self.assertIn(
            new_post, response.context.get('page_obj')
        )

    def test_follow_index_do_not_contain_other_posts(self):
        """
        Новая запись автора не появляется в ленте тех,
        кто на него не подписан.
        """

        another_user = User.objects.create_user(username='another')
        another_client = Client()
        another_client.force_login(another_user)
        Follow.objects.create(
            author=FollowTests.author,
            user=FollowTests.user
        )
        new_post = Post.objects.create(
            text='Текст для проверки подписки',
            author=FollowTests.author
        )
        response = another_client.get(reverse(
            'posts:follow_index'
        ))
        self.assertNotIn(
            new_post, response.context.get('page_obj')
        )
