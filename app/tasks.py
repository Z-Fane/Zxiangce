import random
import time

from flask import current_app, render_template
from flask_mail import Message, Mail

from app import mail, create_app
from app.celery import celery


@celery.task
def send_async_email(to, subject, body, html):
    app = create_app('development')
    with app.app_context():
        msg = Message(subject, recipients=[to])
        msg.body = body
        msg.html = html
        Mail(app).send(msg)


# 接受者，标题，邮件模板，token
def send_email(to, subject, template, **kwargs):
    body = render_template(template + '.txt', **kwargs)
    html = render_template(template + '.html', **kwargs)
    send_async_email.delay(to, subject, body, html)

@celery.task(bind=True)
def long_task(self):
    total=random.randint(10,50)
    for i in range(total):
        self.update_state(state=u'处理中', meta={'current': i, 'total': total})
        time.sleep(1)
    return {'current': 100, 'total': 100, 'result': u'完成'}
