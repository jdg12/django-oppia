# oppia/schedule.py
import datetime
import json

from django.conf import settings
from django.contrib.auth.models import User
from django.db import models
from django.db.models import Max, Sum, Q, F, Count
from django.utils.translation import ugettext_lazy as _
from django.utils import timezone

from oppia.quiz.models import Quiz, QuizAttempt

from tastypie.models import create_api_key

from xml.dom.minidom import *

from course import *

class Schedule(models.Model):
    title = models.TextField(blank=False)
    course = models.ForeignKey(Course)
    default = models.BooleanField(default=False)
    created_date = models.DateTimeField('date created',default=timezone.now)
    lastupdated_date = models.DateTimeField('date updated',default=timezone.now)
    created_by = models.ForeignKey(User)
    
    class Meta:
        verbose_name = _('Schedule')
        verbose_name_plural = _('Schedules')
        
    def __unicode__(self):
        return self.title
    
    def to_xml_string(self):
        doc = Document();
        schedule = doc.createElement('schedule')
        schedule.setAttribute('version',self.lastupdated_date.strftime('%Y%m%d%H%M%S'))
        doc.appendChild(schedule)
        act_scheds = ActivitySchedule.objects.filter(schedule=self)
        for acts in act_scheds:
            act = doc.createElement('activity')
            act.setAttribute('digest',acts.digest)
            act.setAttribute('startdate',acts.start_date.strftime('%Y-%m-%d %H:%M:%S'))
            act.setAttribute('enddate',acts.end_date.strftime('%Y-%m-%d %H:%M:%S'))
            schedule.appendChild(act)
        return doc.toxml()
        
class ActivitySchedule(models.Model):
    schedule = models.ForeignKey(Schedule)
    digest = models.CharField(max_length=100)
    start_date = models.DateTimeField(default=timezone.now)
    end_date = models.DateTimeField(default=timezone.now)
    
    class Meta:
        verbose_name = _('ActivitySchedule')
        verbose_name_plural = _('ActivitySchedules')
