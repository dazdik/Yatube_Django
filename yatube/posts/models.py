"""Документация моделей приложения posts.
Описание полного кода для управления записями в проекте."""

from django.contrib.auth import get_user_model
from django.db import models

CUT_TEXT = 15

User = get_user_model()


class Group(models.Model):
    """Класс Group — модель для группировки постов"""

    title = models.CharField(
        max_length=200,
        verbose_name='Название',
        help_text='Укажите название группы'
    )
    slug = models.SlugField(max_length=100, unique=True)
    description = models.TextField('Описание группы', max_length=300)

    def __str__(self) -> str:
        return self.title


class Post(models.Model):
    """
    Kласс Post — модель для постов
    """

    text = models.TextField(
        verbose_name='Текст',
        help_text='Текст вашего поста'
    )
    pub_date = models.DateTimeField(
        'Дата публикации',
        auto_now_add=True)
    author = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='posts',
        verbose_name='Автор'
    )
    group = models.ForeignKey(
        Group,
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
        related_name='posts',
        verbose_name='Группа',
        help_text='Укажите название вашей группы'
    )
    image = models.ImageField(
        'Картинка',
        upload_to='posts/',
        blank=True
    )

    def __str__(self):
        return self.text[:CUT_TEXT]

    class Meta:
        ordering = ('-pub_date', )
        verbose_name = 'запись'
        verbose_name_plural = 'записи'


class Comment(models.Model):
    """Класс Comment — модель комментирования записей"""

    post = models.ForeignKey(
        Post,
        on_delete=models.CASCADE,
        related_name='comments',
        verbose_name='Пост',
        help_text='Выберите пост'
    )
    author = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='comments',
        verbose_name='Автор'
    )
    text = models.TextField(
        verbose_name='Текст',
        help_text='Введите текст комментария'
    )
    created = models.DateTimeField(
        'Дата публикации',
        auto_now_add=True)

    def __str__(self):
        return self.text[:CUT_TEXT]

    class Meta:
        ordering = ('-created', )
        verbose_name = 'комментарий'
        verbose_name_plural = 'комментарии'


class Follow(models.Model):
    """Класс Follow — модель комментирования записей"""

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='follower',
        null=True,
        verbose_name='Подписчик'
    )
    author = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='following',
        null=True,
        verbose_name='Автор'
    )

    def __str__(self):
        return self.author.username[:CUT_TEXT]

    class Meta:
        verbose_name = 'подписка'
        verbose_name_plural = 'подписки'
        # запрет повторной подписки
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'author'],
                name='unique_follower'
            )
        ]
