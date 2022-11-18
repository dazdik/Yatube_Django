from django.contrib.auth import get_user_model
from django.test import TestCase

from ..models import Comment, Group, Follow, Post

User = get_user_model()

CUT_TEXT = 15


class PostModelTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='auth')
        cls.user_follower = User.objects.create_user(username='follower')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='Тестовый слаг',
            description='Тестовое описание',
        )
        cls.post = Post.objects.create(
            author=cls.user,
            text='Тестовое описание поста',
        )
        cls.comment = Comment.objects.create(
            text='Комментарий для поста',
            author=cls.user,
            post=cls.post,
        )
        cls.follow = Follow.objects.create(
            user=cls.user_follower,
            author=cls.user
        )

    def test_models_have_correct_object_names(self):
        """Проверяем, что у моделей корректно работает __str__."""
        title = (
            (self.group, self.group.title),
            (self.post, self.post.text[:CUT_TEXT]),
            (self.comment, self.comment.text[:CUT_TEXT]),
            (self.follow, self.follow.author.username[:CUT_TEXT]),
        )
        for text, expected_name in title:
            with self.subTest(expected_name=text):
                self.assertEqual(expected_name, str(text))
