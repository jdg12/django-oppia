# oppia/models.py
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
from schedule import *
from activity import *
from cohort import *

models.signals.post_save.connect(create_api_key, sender=User)
    
class Participant(models.Model):
    TEACHER = 'teacher'
    STUDENT = 'student'
    ROLE_TYPES = (
        (TEACHER, 'Teacher'),
        (STUDENT, 'Student'),
    )
    cohort = models.ForeignKey(Cohort)
    user = models.ForeignKey(User)
    role = models.CharField(max_length=20,choices=ROLE_TYPES)
    
    class Meta:
        verbose_name = _('Participant')
        verbose_name_plural = _('Participants')
         
class Message(models.Model):
    course = models.ForeignKey(Course) 
    author = models.ForeignKey(User)
    date_created = models.DateTimeField(default=timezone.now)
    publish_date = models.DateTimeField(default=timezone.now)
    message = models.CharField(max_length=200)
    link = models.URLField(max_length=255)  
    icon = models.CharField(max_length=200)
    
    class Meta:
        verbose_name = _('Message')
        verbose_name_plural = _('Messages')
        
class Badge(models.Model):
    ref = models.CharField(max_length=20)
    name = models.TextField(blank=False)
    description = models.TextField(blank=True)
    default_icon = models.FileField(upload_to="badges")
    points = models.IntegerField(default=100)
    allow_multiple_awards = models.BooleanField(default=False)
    
    class Meta:
        verbose_name = _('Badge')
        verbose_name_plural = _('Badges')
                                
    def __unicode__(self):
        return self.description
    
class Award(models.Model):
    badge = models.ForeignKey(Badge)
    user = models.ForeignKey(User)
    description = models.TextField(blank=False)
    award_date = models.DateTimeField('date awarded',default=timezone.now)
    
    class Meta:
        verbose_name = _('Award')
        verbose_name_plural = _('Awards')
        
    def __unicode__(self):
        return self.description

    @staticmethod
    def get_userawards(user, course=None):
        awards = Award.objects.filter(user=user)
        if course is not None:
            awards = awards.filter(awardcourse__course=course) 
        return awards.count()
    
    def _get_badge(self):
        badge_icon = self.badge.default_icon
        try:
            icon = AwardCourse.objects.get(award=self)
            if icon.course.badge_icon:
                return icon.course.badge_icon
        except AwardCourse.DoesNotExist:
            pass
        return badge_icon
    
    badge_icon = property(_get_badge)
    
class AwardCourse(models.Model):
    award = models.ForeignKey(Award)
    course = models.ForeignKey(Course)
    course_version = models.BigIntegerField(default=0)
      
class Points(models.Model):
    POINT_TYPES = (
        ('signup', 'Sign up'),
        ('userquizattempt', 'Quiz attempt by user'),
        ('firstattempt', 'First quiz attempt'),
        ('firstattemptscore', 'First attempt score'),
        ('firstattemptbonus', 'Bonus for first attempt score'),
        ('quizattempt', 'Quiz attempt'),
        ('quizcreated', 'Created quiz'),
        ('activitycompleted', 'Activity completed'),
        ('mediaplayed', 'Media played'),
        ('badgeawarded', 'Badge awarded'),
        ('coursedownloaded', 'Course downloaded'),
    )
    user = models.ForeignKey(User)
    course = models.ForeignKey(Course,null=True, default=None, on_delete=models.SET_NULL)
    points = models.IntegerField()
    date = models.DateTimeField('date created',default=timezone.now)
    description = models.TextField(blank=False)
    data = models.TextField(blank=True)
    type = models.CharField(max_length=20,choices=POINT_TYPES)

    class Meta:
        verbose_name = _('Points')
        verbose_name_plural = _('Points')
        
    def __unicode__(self):
        return self.description
    
    @staticmethod
    def get_leaderboard(count=0, course=None):

        from oppia.summary.models import UserCourseSummary, UserPointsSummary

        if course is not None:
            users = UserCourseSummary.objects.filter(course=course)
            usersPoints = users.values('user').annotate(points=Sum('points'), badges=Sum('badges_achieved')).order_by('-points')
        else:
            usersPoints = UserPointsSummary.objects.all().values('user','points','badges').order_by('-points')

        if count > 0:
            usersPoints = usersPoints[:count]

        leaderboard = []
        for u in usersPoints:
            user = User.objects.get(pk=u['user'])
            user.badges = 0 if u['badges'] is None else u['badges']
            user.total = 0 if u['points'] is None else u['points']
            leaderboard.append(user)

        return leaderboard
    
    
    @staticmethod
    def get_userscore(user):
        score = Points.objects.filter(user=user).aggregate(total=Sum('points'))
        if score['total'] is None:
            return 0
        return score['total']
    
    @staticmethod
    def media_points(user,start_date=None,end_date=None,course=None):
        results = Points.objects.filter(user=user,type='mediaplayed')
        if start_date:
            results = results.filter(date__gte=start_date)
        if end_date:
            results = results.filter(date__lte=end_date)
        if course:
            results = results.filter(course=course)
        score = results.aggregate(total=Sum('points'))
        if score['total'] is None:
            return 0
        return score['total']
    
    @staticmethod
    def page_points(user,start_date=None,end_date=None,course=None):
        results = Points.objects.filter(user=user,type='activitycompleted')
        if start_date:
            results = results.filter(date__gte=start_date)
        if end_date:
            results = results.filter(date__lte=end_date)
        if course:
            results = results.filter(course=course)
        score = results.aggregate(total=Sum('points'))
        if score['total'] is None:
            return 0
        return score['total']
    
    @staticmethod
    def quiz_points(user,start_date=None,end_date=None,course=None):
        results = Points.objects.filter(user=user).filter(Q(type='firstattempt') | Q(type='firstattemptscore') | Q(type='firstattemptbonus')| Q(type='quizattempt'))
        if start_date:
            results = results.filter(date__gte=start_date)
        if end_date:
            results = results.filter(date__lte=end_date)
        if course:
            results = results.filter(course=course)
        score = results.aggregate(total=Sum('points'))
        if score['total'] is None:
            return 0
        return score['total']
    

    
    
