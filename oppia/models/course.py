# models/course.py
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

models.signals.post_save.connect(create_api_key, sender=User)
    
class Course(models.Model):
    user = models.ForeignKey(User)
    created_date = models.DateTimeField('date created',default=timezone.now)
    lastupdated_date = models.DateTimeField('date updated',default=timezone.now)
    version = models.BigIntegerField()
    title = models.TextField(blank=False)
    description = models.TextField(blank=True, null=True, default=None)
    shortname = models.CharField(max_length=200)
    filename = models.CharField(max_length=200)
    badge_icon = models.FileField(upload_to="badges",blank=True, default=None)
    is_draft = models.BooleanField(default=False)
    is_archived = models.BooleanField(default=False)
   
    class Meta:
        verbose_name = _('Course')
        verbose_name_plural = _('Courses')
        
    def __unicode__(self):
        return self.get_title(self)
    
    def getAbsPath(self):
        return settings.COURSE_UPLOAD_DIR + self.filename
    
    def get_title(self,lang='en'):
        try:
            titles = json.loads(self.title)
            if lang in titles:
                return titles[lang]
            else:
                for l in titles:
                    return titles[l]
        except:
            pass
        return self.title 
     
    def is_first_download(self,user):
        no_attempts = Tracker.objects.filter(user=user,course=self, type='download').count()
        is_first_download = False
        if no_attempts == 1:
            is_first_download = True
        return is_first_download
    
    def no_downloads(self):
        no_downloads = Tracker.objects.filter(course=self, type='download').count()
        return no_downloads
    
    def no_distinct_downloads(self):
        no_distinct_downloads = Tracker.objects.filter(course=self, type='download').values('user_id').distinct().count()
        return no_distinct_downloads
    
    def get_default_schedule(self):
        try:
            schedule = Schedule.objects.get(default=True,course = self)
        except Schedule.DoesNotExist:
            return None
        return schedule
    
    def get_activity_today(self):
        return Tracker.objects.filter(course=self,
                                      tracker_date__day=timezone.now().day,
                                      tracker_date__month=timezone.now().month,
                                      tracker_date__year=timezone.now().year).count()
       
    def get_activity_week(self):
        now = datetime.datetime.now()
        last_week = datetime.datetime(now.year, now.month, now.day) - datetime.timedelta(days=7)
        return Tracker.objects.filter(course=self,
                                      tracker_date__gte=last_week).count()
                                      
    def has_quizzes(self):
        quiz_count = Activity.objects.filter(section__course=self,type=Activity.QUIZ).count()
        if quiz_count > 0:
            return True
        else:
            return False
    
    def has_feedback(self):
        fb_count = Activity.objects.filter(section__course=self,type='feedback').count()
        if fb_count > 0:
            return True
        else:
            return False
            
    def get_tags(self):
        tags = Tag.objects.filter(coursetag__course=self)
        str = ""
        for t in tags:
            str = str + t.name + ", "
        return str[:-2]
    
    def sections(self):
        sections = Section.objects.filter(course=self).order_by('order')
        return sections
    
    def get_no_activities(self):
        return Activity.objects.filter(section__course=self, baseline=False).count()
    
    def get_no_quizzes(self):
        return Activity.objects.filter(section__course=self,type=Activity.QUIZ,baseline=False).count()

    def get_no_media(self):
        return Media.objects.filter(course=self).count()
    
    @staticmethod
    def get_pre_test_score(course,user):
        try:
            baseline = Activity.objects.get(section__course=course,type=Activity.QUIZ,section__order=0)
        except Activity.DoesNotExist:
            return None
        
        try:
            quiz = Quiz.objects.get(quizprops__value=baseline.digest, quizprops__name="digest")
        except Quiz.DoesNotExist:
            return None
        
        attempts = QuizAttempt.objects.filter(quiz=quiz, user=user)
        if attempts.count() != 0:
            max_score = 100*float(attempts.aggregate(max=Max('score'))['max']) / float(attempts[0].maxscore)
            return max_score
        else:
            return None
    
    @staticmethod
    def get_no_quizzes_completed(course,user):
        acts = Activity.objects.filter(section__course=course,baseline=False, type=Activity.QUIZ).values_list('digest')
        return Tracker.objects.filter(course=course,user=user,completed=True,digest__in=acts).values_list('digest').distinct().count()
    
    @staticmethod
    def get_activities_completed(course,user):
        acts = Activity.objects.filter(section__course=course,baseline=False).values_list('digest')
        return Tracker.objects.filter(course=course,user=user,completed=True,digest__in=acts).values_list('digest').distinct().count()
    
    @staticmethod
    def get_points(course,user):
        points = Points.objects.filter(course=course,user=user).aggregate(total=Sum('points'))
        return points['total']
    
    @staticmethod
    def get_badges(course,user):
        return Award.objects.filter(user=user,awardcourse__course=course).count()

    @staticmethod
    def get_media_viewed(course,user):
        acts = Media.objects.filter(course=course).values_list('digest')
        return Tracker.objects.filter(course=course,user=user,digest__in=acts).values_list('digest').distinct().count()


class CourseManager(models.Model):
    course = models.ForeignKey(Course)
    user = models.ForeignKey(User)
    
    class Meta:
        verbose_name = _('Course Manager')
        verbose_name_plural = _('Course Managers')

class Tag(models.Model):
    name = models.TextField(blank=False)
    created_date = models.DateTimeField('date created',default=timezone.now)
    created_by = models.ForeignKey(User)
    courses = models.ManyToManyField(Course, through='CourseTag')
    description = models.TextField(blank=True, null=True, default=None)
    order_priority = models.IntegerField(default=0)
    highlight = models.BooleanField(default=False)
    icon = models.FileField(upload_to="tags", null=True, blank=True, default=None) 
    
    class Meta:
        verbose_name = _('Tag')
        verbose_name_plural = _('Tags')
        
    def __unicode__(self):
        return self.name


class CourseTag(models.Model):
    course = models.ForeignKey(Course)
    tag = models.ForeignKey(Tag)
    
    class Meta:
        verbose_name = _('Course Tag')
        verbose_name_plural = _('Course Tags')

class Section(models.Model):
    course = models.ForeignKey(Course)
    order = models.IntegerField()
    title = models.TextField(blank=False)
    
    class Meta:
        verbose_name = _('Section')
        verbose_name_plural = _('Sections')
        
    def __unicode__(self):
        return self.get_title()
    
    def get_title(self,lang='en'):
        try:
            titles = json.loads(self.title)
            if lang in titles:
                return titles[lang]
            else:
                for l in titles:
                    return titles[l]
        except:
            pass
        return self.title
    
    def activities(self):
        activities = Activity.objects.filter(section=self).order_by('order')
        return activities
    




