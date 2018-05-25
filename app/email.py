from threading import Thread

from flask import render_template, current_app
from flask_mail import Message

from app import mail
from app.celery import celery


@celery.task
def send_async_email(app, msg):
    with app.app_context():
        mail.send(msg)


# 接受者，标题，邮件模板，token
def send_email(to, subject, template, **kwargs):
    app = current_app._get_current_object()
    msg = Message(subject,
                  recipients=[to])
    msg.body = render_template(template + '.txt', **kwargs)
    msg.html = render_template(template + '.html', **kwargs)

    send_async_email.delay(app,msg)
