# quiz/questions.py
from django.apps import apps
from django.contrib.auth.models import User
from django.core import serializers
from django.db import models
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _

import datetime

class Question(models.Model):
    QUESTION_TYPES = (
        ('multichoice', 'Multiple choice'),
        ('shortanswer', 'Short answer'),
        ('matching', 'Matching'),
        ('numerical', 'Numerical'),
        ('multiselect', 'Multiple select'),
        ('description', 'Information only'),
        ('essay', 'Essay question'),
    )
    owner = models.ForeignKey(User)
    created_date = models.DateTimeField('date created',default=timezone.now)
    lastupdated_date = models.DateTimeField('date updated',default=timezone.now)
    title = models.TextField(blank=False)  
    type = models.CharField(max_length=15,choices=QUESTION_TYPES, default='multichoice') 
    
    class Meta:
        verbose_name = _('Question')
        verbose_name_plural = _('Questions')
        
    def __unicode__(self):
        return self.title
    
    def get_maxscore(self):
        props = QuestionProps.objects.get(question=self,name='maxscore')
        return float(props.value);

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
    
class Quiz(models.Model):
    owner = models.ForeignKey(User)
    created_date = models.DateTimeField('date created',default=timezone.now)
    lastupdated_date = models.DateTimeField('date updated',default=timezone.now)
    draft = models.BooleanField(default=False)
    deleted = models.BooleanField(default=False)
    title = models.TextField(blank=False)
    description = models.TextField(blank=True)
    questions = models.ManyToManyField(Question, through='QuizQuestion')
    
    class Meta:
        verbose_name = _('Quiz')
        verbose_name_plural = _('Quizzes')
        
    def __unicode__(self):
        return self.title
    
    def no_attempts(self):
        no_attempts = QuizAttempt.objects.filter(quiz=self).count()
        return no_attempts
    
    def avg_score(self):
        # TODO - sure this could be tidied up
        attempts = QuizAttempt.objects.filter(quiz=self)
        total = 0
        for a in attempts:
            total = total + a.get_score_percent()
        if self.no_attempts > 0:
            avg_score = int(total/self.no_attempts())
        else:
            avg_score = 0
        return avg_score
