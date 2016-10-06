# quiz/models/models.py
from django.apps import apps
from django.contrib.auth.models import User
from django.core import serializers
from django.db import models
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _

from questions import *
from quiz import *

import datetime

class Response(models.Model):
    owner = models.ForeignKey(User)
    question = models.ForeignKey(Question)
    created_date = models.DateTimeField('date created',default=timezone.now)
    lastupdated_date = models.DateTimeField('date updated',default=timezone.now)
    score = models.DecimalField(default=0,decimal_places=2, max_digits=6)
    title = models.TextField(blank=False)
    order = models.IntegerField(default=1)
    
    class Meta:
        verbose_name = _('Response')
        verbose_name_plural = _('Responses')
        
    def __unicode__(self):
        return self.title
    
class QuizQuestion(models.Model):
    quiz = models.ForeignKey(Quiz)
    question = models.ForeignKey(Question)
    order = models.IntegerField(default=1)
    
    class Meta:
        verbose_name = _('QuizQuestion')
        verbose_name_plural = _('QuizQuestions')
    
    
class ResponseProps(models.Model):
    response = models.ForeignKey(Response)
    name = models.CharField(max_length=200)
    value = models.TextField(blank=True)
    
    class Meta:
        verbose_name = _('ResponseProp')
        verbose_name_plural = _('ResponseProps')
        
    def __unicode__(self):
        return self.name  


class QuizAttemptResponse(models.Model):
    quizattempt = models.ForeignKey(QuizAttempt)
    question = models.ForeignKey(Question)
    score = models.DecimalField(decimal_places=2, max_digits=6)
    text = models.TextField(blank=True)
    
    class Meta:
        verbose_name = _('QuizAttemptResponse')
        verbose_name_plural = _('QuizAttemptResponses')
       
    def get_score_percent(self):
        if self.question.get_maxscore() > 0:
            percent = int(round(float(self.score) * 100 / self.question.get_maxscore()))
        else:
            percent = 0
        return percent
