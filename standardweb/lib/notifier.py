from standardweb.lib import api
from standardweb.lib import email
from standardweb.lib import realtime
from standardweb.tasks import email_news_post_all


def notify_new_message(message, send_email=True):
    from_user = message.from_user
    to_user = message.to_user
    to_player = message.to_player

    if to_user:
        realtime.new_message(to_user, message)
        realtime.unread_message_count(to_user)

        if send_email:
            email.send_new_message_email(to_user, message)

    if to_player:
        api.new_message(to_player, from_user)


def notify_news_post(post):
    email_news_post_all.apply_async((
        post.id,
    ))
