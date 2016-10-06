# models/cohort.py

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

from oppia.models.course import *
from oppia.models.schedule import *

class Cohort(models.Model): 
    description = models.CharField(max_length=100)
    start_date = models.DateTimeField(default=timezone.now)
    end_date = models.DateTimeField(default=timezone.now)
    schedule = models.ForeignKey(Schedule,null=True, blank=True, default=None, on_delete=models.SET_NULL)
    
    class Meta:
        verbose_name = _('Cohort')
        verbose_name_plural = _('Cohorts')
        
    def __unicode__(self):
        return self.description
    
    def no_student_members(self):
        return Participant.objects.filter(cohort=self, role=Participant.STUDENT).count()
    
    def no_teacher_members(self):
        return Participant.objects.filter(cohort=self, role=Participant.TEACHER).count()
    
    
    @staticmethod
    def student_member_now(course,user):
        now = timezone.now()
        cohorts = Cohort.objects.filter(coursecohort__course=course,start_date__lte=now,end_date__gte=now)
        for c in cohorts:
            participants = c.participant_set.filter(user=user,role=Participant.STUDENT)
            for p in participants:
                return c
        return None
    
    @staticmethod
    def teacher_member_now(course,user):
        now = timezone.now()
        cohorts = Cohort.objects.filter(coursecohort__course=course,start_date__lte=now,end_date__gte=now)
        for c in cohorts:
            participants = c.participant_set.filter(user=user,role=Participant.TEACHER)
            for p in participants:
                return c
        return None
    
    @staticmethod
    def member_now(course,user):
        now = timezone.now()
        cohorts = Cohort.objects.filter(coursecohort__course=course,start_date__lte=now,end_date__gte=now)
        for c in cohorts:
            participants = c.participant_set.filter(user=user)
            for p in participants:
                return c
        return None

    def get_courses(self):
        courses = Course.objects.filter(coursecohort__cohort = self).order_by('title')
        return courses

    def get_leaderboard(self, count=0):
        users = User.objects.filter(participant__cohort=self, 
                                    participant__role=Participant.STUDENT, 
                                    points__course__coursecohort__cohort=self) \
                            .annotate(total=Sum('points__points')) \
                            .order_by('-total')
         
        if count != 0:
            users = users[:count]
   
        for u in users:
            u.badges = Award.objects.filter(user=u, awardcourse__course__coursecohort__cohort=self).count()
            if u.total is None:
                u.total = 0
        return users
    
class CourseCohort(models.Model):
    course = models.ForeignKey(Course) 
    cohort = models.ForeignKey(Cohort)  
  
    class Meta:
        unique_together = ("course", "cohort")
