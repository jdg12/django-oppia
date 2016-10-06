# oppia/uploader.py

import codecs
import json
import shutil
import xml.dom.minidom
from xml.dom.minidom import Node
from zipfile import ZipFile

import os
from django.conf import settings
from django.contrib import messages
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _

from oppia.models import Course, Section, Activity, Media
from oppia.quiz.models import Quiz, Question, QuizQuestion, Response, ResponseProps, QuestionProps, QuizProps


def handle_uploaded_file(f, extract_path, request, user):
    zipfilepath = settings.COURSE_UPLOAD_DIR + f.name

    with open(zipfilepath, 'wb+') as destination:
        for chunk in f.chunks():
            destination.write(chunk)

    ZipFile(zipfilepath).extractall(path=extract_path)

    mod_name = ''
    for dir in os.listdir(extract_path)[:1]:
        mod_name = dir

    # check there is at least a sub dir
    if mod_name == '':
        messages.info(request, _("Invalid course zip file"), extra_tags="danger")
        return False

    # check that the module.xml file exists
    if not os.path.isfile(os.path.join(extract_path, mod_name, "module.xml")):
        messages.info(request, _("Zip file does not contain a module.xml file"), extra_tags="danger")
        return False

    # parse the module.xml file
    xml_path = os.path.join(extract_path, mod_name, "module.xml")
    doc = xml.dom.minidom.parse(xml_path)
    meta_info = parse_course_meta(doc)

    new_course = False
    oldsections = []
    old_course_filename = None

    # Find if course already exists
    try:
        course = Course.objects.get(shortname=meta_info['shortname'])
        # check that the current user is allowed to wipe out the other course
        if course.user != user:
            messages.info(request, _("Sorry, only the original owner may update this course"))
            return False
        # check if course version is older
        if course.version > meta_info['versionid']:
            messages.info(request, _("A newer version of this course already exists"))
            return False

        # obtain the old sections
        oldsections = list(Section.objects.filter(course=course).values_list('pk', flat=True))
        # wipe out old media
        oldmedia = Media.objects.filter(course=course)
        oldmedia.delete()

        old_course_filename = course.filename
        course.lastupdated_date = timezone.now()

    except Course.DoesNotExist:
        course = Course()
        course.is_draft = True
        new_course = True

    course.shortname = meta_info['shortname']
    course.title = meta_info['title']
    course.description = meta_info['description']
    course.version = meta_info['versionid']
    course.user = user
    course.filename = f.name
    course.save()

    parse_course_contents(request, doc, course, user, new_course)
    clean_old_course(request, oldsections, old_course_filename, course)

    tmp_path = replace_zip_contents(xml_path, doc, mod_name, extract_path)
    # Extract the final file into the courses area for preview
    zipfilepath = settings.COURSE_UPLOAD_DIR + f.name
    shutil.copy(tmp_path+".zip", zipfilepath)

    course_preview_path = settings.MEDIA_ROOT + "courses/"
    ZipFile(zipfilepath).extractall(path=course_preview_path)

    # remove the temp upload files
    shutil.rmtree(extract_path, ignore_errors=True)

    return course


def parse_course_contents(req, xml_doc, course, user, new_course):
    # add in any baseline activities
    for meta in xml_doc.getElementsByTagName("meta")[:1]:
        if meta.getElementsByTagName("activity").length > 0:
            section = Section(
                course = course,
                title = '{"en": "Baseline"}',
                order = 0
            )
            section.save()
            for a in meta.getElementsByTagName("activity"):
                parse_and_save_activity(req, user, section, a, new_course, is_baseline=True)

    # add all the sections and activities
    for structure in xml_doc.getElementsByTagName("structure")[:1]:

        if structure.getElementsByTagName("section").length == 0:
            course.delete()
            messages.info(req, _("There don't appear to be any activities in this upload file."))
            return

        for idx, s in enumerate(structure.getElementsByTagName("section")):

            # Check if the section contains any activity (to avoid saving an empty one)
            activities = s.getElementsByTagName("activities")[:1]
            if not activities or activities[0].getElementsByTagName("activity").length == 0:
                messages.info(req, _("Section ") + str(idx+1) + _(" does not contain any activity."))
                continue

            title = {}
            for t in s.childNodes:
                if t.nodeName == 'title':
                    title[t.getAttribute('lang')] = t.firstChild.nodeValue
            section = Section(
                course = course,
                title = json.dumps(title),
                order = s.getAttribute("order")
            )
            section.save()

            for activities in s.getElementsByTagName("activities")[:1]:
                for a in activities.getElementsByTagName("activity"):
                    parse_and_save_activity(req, user, section, a, new_course)

    # add all the media
    for file in xml_doc.lastChild.lastChild.childNodes:
        if file.nodeName == 'file':
            media = Media()
            media.course = course
            media.filename = file.getAttribute("filename")
            media.download_url = file.getAttribute("download_url")
            media.digest = file.getAttribute("digest")

            # get any optional attributes
            for attrName, attrValue in file.attributes.items():
                if attrName == "length":
                    media.media_length = attrValue
                if attrName == "filesize":
                    media.filesize = attrValue

            media.save()


def parse_and_save_activity(req, user, section, act, new_course, is_baseline=False):
    """
    Parses an Activity XML and saves it to the DB
    :param section: section the activity belongs to
    :param act: a XML DOM element containing a single activity
    :param is_baseline: is the activity part of the baseline?
    :return: None
    """
    temp_title = {}
    for t in act.getElementsByTagName("title"):
        temp_title[t.getAttribute('lang')] = t.firstChild.nodeValue
    title = json.dumps(temp_title)

    content = ""
    act_type = act.getAttribute("type")
    if act_type == "page":
        temp_content = {}
        for t in act.getElementsByTagName("location"):
            if t.firstChild and t.getAttribute('lang'):
                temp_content[t.getAttribute('lang')] = t.firstChild.nodeValue
        content = json.dumps(temp_content)
    elif act_type == "quiz":
        for c in act.getElementsByTagName("content"):
            content = c.firstChild.nodeValue
    elif act_type == "feedback":
        for c in act.getElementsByTagName("content"):
            content = c.firstChild.nodeValue
    elif act_type == "resource":
        for c in act.getElementsByTagName("location"):
            content = c.firstChild.nodeValue
    elif act_type == "url":
        temp_content = {}
        for t in act.getElementsByTagName("location"):
            if t.firstChild and t.getAttribute('lang'):
                temp_content[t.getAttribute('lang')] = t.firstChild.nodeValue
        content = json.dumps(temp_content)
    else:
        content = None

    image = None
    if act.getElementsByTagName("image"):
        for i in act.getElementsByTagName("image"):
            image = i.getAttribute('filename')

    if act.getElementsByTagName("description"):
        description = {}
        for d in act.getElementsByTagName("description"):
            if d.firstChild and d.getAttribute('lang'):
                description[d.getAttribute('lang')] = d.firstChild.nodeValue
        description = json.dumps(description)
    else:
        description = None

    digest = act.getAttribute("digest")
    existed = False
    try:
        activity = Activity.objects.get(digest=digest)
        existed = True
    except Activity.DoesNotExist:
        activity = Activity()

    activity.section = section
    activity.title = title
    activity.type = act_type
    activity.order = act.getAttribute("order")
    activity.digest = act.getAttribute("digest")
    activity.baseline = is_baseline
    activity.image = image
    activity.content = content
    activity.description = description

    if not existed:
        # Only show the message if the course existed previously
        if not new_course:
            messages.warning(req, _('Activity "%(act)s"(%(digest)s) did not exist previously.') % {'act': activity, 'digest':activity.digest})
    '''
    If we also want to show the activities that previously existed, uncomment this block
    else:
        messages.info(req, _('Activity "%(act)s"(%(digest)s) previously existed. Updated with new information') % {'act': activity, 'digest':activity.digest})
    '''

    if act_type == "quiz":
        updated_json = parse_and_save_quiz(req, user, activity)
        # we need to update the JSON contents both in the XML and in the activity data
        act.getElementsByTagName("content")[0].firstChild.nodeValue = updated_json
        activity.content = updated_json

    activity.save()


def parse_and_save_quiz(req, user, activity):
    """
    Parses an Activity XML that is a Quiz and saves it to the DB
    :parm user: the user that uploaded the course
    :param activity: a XML DOM element containing the activity
    :return: None
    """

    quiz_obj = json.loads(activity.content)
    # first of all, we find the quiz digest to see if it is already saved
    if quiz_obj['props']['digest']:
        quiz_digest = quiz_obj['props']['digest']
        try:
            quiz = Quiz.objects.get(quizprops__value=quiz_digest, quizprops__name="digest")
        except Quiz.DoesNotExist:
            quiz = None

    if quiz is not None:
        quiz_act = Activity.objects.get(digest=quiz_digest)
        updated_content = quiz_act.content
    else:
        updated_content = create_quiz(user, quiz_obj)

    return updated_content


def create_quiz(user, quiz_obj):

    quiz = Quiz()
    quiz.owner = user
    quiz.title = quiz_obj['title']
    quiz.description = quiz_obj['description']
    quiz.save()

    quiz_obj['id'] = quiz.pk

    for prop in quiz_obj['props']:
        if prop is not 'id':
            QuizProps(
                quiz=quiz, name=prop,
                value=quiz_obj['props'][prop]
            ).save()

    for q in quiz_obj['questions']:

        question = Question(owner=user,
                type= q['question']['type'],
                title=q['question']['title'])
        question.save()

        quizQuestion = QuizQuestion( quiz = quiz,
            question = question, order = q['order'])
        quizQuestion.save()

        q['id'] = quizQuestion.pk
        q['question']['id'] = question.pk

        for prop in q['question']['props']:
            if prop is not 'id':
                QuestionProps(
                    question=question, name=prop,
                    value = q['question']['props'][prop]
                ).save()

        for r in q['question']['responses']:
            response = Response(
                owner = user,
                question = question,
                title = r['title'],
                score = r['score'],
                order = r['order']
            )
            response.save()
            r['id'] = response.pk

            for prop in r['props']:
                if prop is not 'id':
                    ResponseProps(
                        response= response, name = prop,
                        value = r['props'][prop]
                    ).save()

    return json.dumps(quiz_obj)

def parse_course_meta(xml_doc):

    meta_info = { 'versionid': 0, 'shortname':'' }
    for meta in xml_doc.getElementsByTagName("meta")[:1]:
        for v in meta.getElementsByTagName("versionid")[:1]:
            meta_info['versionid'] = int(v.firstChild.nodeValue)

        temp_title = {}
        for t in meta.childNodes:
            if t.nodeName == "title":
                temp_title[t.getAttribute('lang')] = t.firstChild.nodeValue
        meta_info['title'] = json.dumps(temp_title)

        temp_description = {}
        for t in meta.childNodes:
            if t.nodeName == "description":
                if t.firstChild is not None:
                    temp_description[t.getAttribute('lang')] = t.firstChild.nodeValue
                else:
                    temp_description[t.getAttribute('lang')] = None
        meta_info['description'] = json.dumps(temp_description)

        for sn in meta.getElementsByTagName("shortname")[:1]:
            meta_info['shortname'] = sn.firstChild.nodeValue

    return meta_info

def replace_zip_contents(xml_path, xml_doc, mod_name, dest):
    fh = codecs.open(xml_path, mode="w", encoding="utf-8")
    new_xml = xml_doc.toxml("utf-8").decode('utf-8').replace("&amp;", "&").replace("&quot;","\"")
    fh.write(new_xml)
    fh.close()

    tmp_zipfilepath = os.path.join(dest, 'tmp_course')
    shutil.make_archive(tmp_zipfilepath, 'zip', dest, base_dir=mod_name)
    return tmp_zipfilepath

def clean_old_course(req, oldsections, old_course_filename, course):
    for section in oldsections:
        sec = Section.objects.get(pk=section)
        for act in sec.activities():
            messages.info(req, _('Activity "%(act)s"(%(digest)s) is no longer in the course.') % {'act': act, 'digest':act.digest})
        sec.delete()

    if old_course_filename is not None and old_course_filename != course.filename:
        try:
            os.remove(settings.COURSE_UPLOAD_DIR + old_course_filename)
        except OSError:
            pass