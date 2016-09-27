# oppia/activity.py
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

from oppia.course import *

class Activity(models.Model):
    QUIZ = 'quiz'
    MEDIA = 'media'
    PAGE = 'page'
    FEEDBACK = 'feedback'
    ACTIVITY_TYPES = (
        (QUIZ, 'Quiz'),
        (MEDIA, 'Media'),
        (PAGE, 'Page'),
        (FEEDBACK, 'Feedback')
    )
    
    section = models.ForeignKey(Section)
    order = models.IntegerField()
    title = models.TextField(blank=False)
    type = models.CharField(max_length=10)
    digest = models.CharField(max_length=100)
    baseline = models.BooleanField(default=False)
    image = models.TextField(blank=True, null=True, default=None)
    content = models.TextField(blank=True, null=True, default=None)
    description = models.TextField(blank=True, null=True, default=None)
    
    def __unicode__(self):
        return self.get_title()
    
    class Meta:
        verbose_name = _('Activity')
        verbose_name_plural = _('Activities')
        
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
    
    def get_content(self,lang='en'):
        try:
            contents = json.loads(self.content)
            if lang in contents:
                return contents[lang]
            else:
                for l in contents:
                    return contents[l]
        except:
            pass
        return self.content 
    
    def get_next_activity(self):
        try:
            next_activity = Activity.objects.get(section__course=self.section.course,order=self.order+1,section=self.section)
        except Activity.DoesNotExist:
            try:
                next_activity = Activity.objects.get(section__course=self.section.course, section__order=self.section.order+1,order=1)
            except Activity.DoesNotExist:
                next_activity = None
        return next_activity
        
    def get_previous_activity(self):
        try:
            prev_activity = Activity.objects.get(section__course=self.section.course,order=self.order-1,section=self.section)
        except Activity.DoesNotExist:
            try:
                max_order = Activity.objects.filter(section__course=self.section.course,section__order=self.section.order-1).aggregate(max_order=Max('order'))
                prev_activity = Activity.objects.get(section__course=self.section.course,section__order=self.section.order-1,order=max_order['max_order'])
            except:
                prev_activity = None        
        return prev_activity
    
class Media(models.Model):
    course = models.ForeignKey(Course)
    digest = models.CharField(max_length=100)
    filename = models.CharField(max_length=200)
    download_url = models.URLField()
    filesize = models.BigIntegerField(default=None,blank=True,null=True)
    media_length = models.IntegerField(default=None,blank=True,null=True)
    
    class Meta:
        verbose_name = _('Media')
        verbose_name_plural = _('Media')
        
    def __unicode__(self):
        return self.filename
    
class Tracker(models.Model):
    user = models.ForeignKey(User)
    submitted_date = models.DateTimeField('date submitted',default=timezone.now)
    tracker_date = models.DateTimeField('date tracked',default=timezone.now)
    ip = models.GenericIPAddressField()
    agent = models.TextField(blank=True)
    digest = models.CharField(max_length=100)
    data = models.TextField(blank=True)
    course = models.ForeignKey(Course,null=True, blank=True, default=None, on_delete=models.SET_NULL)
    type = models.CharField(max_length=10,null=True, blank=True, default=None)
    completed = models.BooleanField(default=False)
    time_taken = models.IntegerField(default=0)
    activity_title = models.TextField(blank=True, null=True, default=None)
    section_title = models.TextField(blank=True, null=True, default=None)
    uuid = models.TextField(blank=True, null=True, default=None)
    lang = models.CharField(max_length=10,null=True, blank=True, default=None)
    
    class Meta:
        verbose_name = _('Tracker')
        verbose_name_plural = _('Trackers')
        
    def __unicode__(self):
        return self.agent
    
    def is_first_tracker_today(self):
        olddate = timezone.now() + datetime.timedelta(hours=-24)
        no_attempts_today = Tracker.objects.filter(user=self.user,digest=self.digest,completed=True,submitted_date__gte=olddate).count()
        if no_attempts_today == 1:
            return True
        else:
            return False
    
    def get_activity_type(self):
        activities = Activity.objects.filter(digest=self.digest)
        for a in activities:
            return a.type
        media = Media.objects.filter(digest=self.digest)
        for m in media:
            return "media"
        return None
     
    def get_media_title(self):
        media = Media.objects.filter(digest=self.digest)
        for m in media:
            return m.filename
        return None
           
    def get_activity_title(self, lang='en'):
        media = Media.objects.filter(digest=self.digest)
        print media
        for m in media:
            return m.filename
        try:
            activity = Activity.objects.filter(digest=self.digest)
            for a in activity:
                print a.title
                titles = json.loads(a.title)
                if lang in titles:
                    return titles[lang]
                else:
                    for l in titles:
                        return titles[l]
        except:
            pass
        return self.activity_title
    
    def get_section_title(self, lang='en'):
        try:
            titles = json.loads(self.section_title)
            if lang in titles:
                return titles[lang]
            else:
                for l in titles:
                    return titles[l]
        except:
            pass
        return self.section_title
    
    def activity_exists(self):
        activities = Activity.objects.filter(digest=self.digest).count()
        if activities >= 1:
            return True
        media = Media.objects.filter(digest=self.digest).count()
        if media >= 1:
            return True
        return False
 
    @staticmethod
    def has_completed_trackers(course,user):
        count = Tracker.objects.filter(user=user, course=course,completed=True).count()        
        if count > 0:
            return True
        return False
     
    @staticmethod
    def to_xml_string(course,user):
        doc = Document();
        trackerXML = doc.createElement('trackers')
        doc.appendChild(trackerXML)
        trackers = Tracker.objects.filter(user=user, course=course)
        for t in trackers:
            track = doc.createElement('tracker')
            track.setAttribute('digest', t.digest)
            track.setAttribute('submitteddate', t.submitted_date.strftime('%Y-%m-%d %H:%M:%S'))
            track.setAttribute('completed', str(t.completed))
            track.setAttribute('type', t.type)
            if t.type == 'quiz':
                try:
                    quiz = doc.createElement('quiz')
                    data = json.loads(t.data)
                    quiz_attempt = QuizAttempt.objects.filter(instance_id=data['instance_id'],user=user).order_by('-submitted_date')[:1]
                    quiz.setAttribute('score', str(quiz_attempt[0].score))
                    quiz.setAttribute('maxscore', str(quiz_attempt[0].maxscore))
                    quiz.setAttribute('submitteddate', quiz_attempt[0].submitted_date.strftime('%Y-%m-%d %H:%M:%S'))
                    quiz.setAttribute('passed', str(t.completed))
                    quiz.setAttribute("course", course.shortname)
                    track.appendChild(quiz)
                except ValueError:
                    pass  
                except IndexError:
                    pass  
            trackerXML.appendChild(track)
        return doc.toxml() 
    
    @staticmethod
    def activity_views(user,type,start_date=None,end_date=None,course=None):
        results = Tracker.objects.filter(user=user,type=type)
        if start_date:
            results = results.filter(submitted_date__gte=start_date)
        if end_date:
            results = results.filter(submitted_date__lte=end_date)
        if course:
            results = results.filter(course=course)
        return results.count()
    
    @staticmethod
    def activity_secs(user,type,start_date=None,end_date=None,course=None):
        results = Tracker.objects.filter(user=user,type=type)
        if start_date:
            results = results.filter(submitted_date__gte=start_date)
        if end_date:
            results = results.filter(submitted_date__lte=end_date)
        if course:
            results = results.filter(course=course)
        time = results.aggregate(total=Sum('time_taken'))
        if time['total'] is None:
            return 0
        return time['total']
    
    def get_lang(self):
        try:
            json_data = json.loads(self.data)
        except ValueError:
            return None
        
        if 'lang' in json_data:
            return json_data['lang']
