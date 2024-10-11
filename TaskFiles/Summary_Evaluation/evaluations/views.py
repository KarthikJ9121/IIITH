from django.shortcuts import render
from django.http import JsonResponse
from os import listdir, path
from django.views.decorators.csrf import csrf_exempt
from .utils import *
from TeluguTokenizer.summ_quality_check import *
import json, os
from django.conf import settings
from django.http import HttpResponse, Http404
from django.shortcuts import redirect
import datetime
from .forms import *

debug = False

# Create your views here.
def index_page(request):
	return redirect(load_annotation_files)

def home_page(request):
	return render(request, 'users/home.html')

def about_page(request):
	return render(request, 'users/about.html')

def contact_page(request):
	return render(request, 'users/contact_us.html')

def import_data(request):
	base_folder_path = 'static/datasets/'

	form = upload()
	if request.method == "POST":
		form = upload(request.POST,request.FILES)
		if form.is_valid():
			file_ = request.FILES['file']

			output_file_path = base_folder_path + file_.name

			if debug:
				print("File Name: ", file_.name)
				print("Output FilePath: ", output_file_path)
			
			if path.exists(output_file_path):
				return HttpResponse('File Already Exists!')
			else:
				with open(output_file_path, 'wb+') as fp:
					for chunk in file_.chunks():
						fp.write(chunk)

			return HttpResponse("File Uploaded Successfully!")
		else:
			form = upload()
	return render(request, 'tasks/import_data.html', {'form':form})

# Load the annotation files from the task folder
def load_annotation_files(request):
	context = {}

	base_url = 'static/datasets/'
	task_name = 'summ'
	context['task_name'] = task_name

	context['task_folders'] = load_annotation_stats(base_url)

	if task_name=='summ':
		return render(request, 'tasks/evaluation/index.html', context)
	else:
		return render(request, 'tasks/404.html')


# Load the task statistics from the json file
def load_tasks(request, file_name):
	task_name = 'summ'
	print("Task Name: ", task_name, "File Name: ", file_name)
	context = {}

	base_url = 'static/datasets/'
	if not file_name.endswith(".jsonl"):
		file_name += ".jsonl"
	json_path = path.join(base_url, file_name)

	context['articles'] = read_jsonl(json_path, return_ids=True)
	context['json_path'] = json_path
	request.session['json_path'] = json_path

	if task_name == 'summ':
		return render(request, 'tasks/evaluation/evaluate_data.html', context)
	else:
		return render(request, 'tasks/404.html')


def download_data(request, file_name):
	task_name = 'summ'
	print("Task Name: ", task_name, "File Name: ", file_name)
	context = {}

	base_url = 'static/datasets/'
	if not file_name.endswith(".jsonl"):
		file_name += ".jsonl"
	json_path = path.join(base_url, file_name)

	context['articles'] = read_jsonl(json_path, return_ids=True)
	context['json_path'] = json_path

	print("Date Time: ", datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S"))
	output_file_name = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S") + "_" + os.path.basename(json_path)
	if os.path.exists(json_path):
		with open(json_path, 'rb') as fh:
			response = HttpResponse(fh.read(), content_type="application/vnd.ms-excel")
			response['Content-Disposition'] = 'inline; filename=' + output_file_name 
			return response
	raise Http404


def fetch_feedback(request, file_name):
	task_name = 'summ'
	file_name_str = file_name

	if debug:
		print("Task Name: ", task_name, "File Name: ", file_name)
	context = {}

	base_url = 'static/datasets/'
	if not file_name.endswith(".jsonl"):
		file_name = file_name + ".jsonl"
	json_path = path.join(base_url, file_name)
	evaluations, overall_feedback = read_evaluated_comments(json_path)

	feedbacks_json_path = 'static/feedbacks/final_feedbacks.jsonl'
	feedbacks = []
	if os.path.exists(feedbacks_json_path):
		feedbacks = read_feedbacks(feedbacks_json_path)

	feedback_content = ""
	for entry in feedbacks:
		if str(entry.get('file_name', ''))==file_name_str:
			feedback_content = str(entry.get('content', ''))

	context['feedback'] = feedback_content
	context['overall_feedback'] = overall_feedback
	context['evals'] = evaluations
	context['filename'] = file_name_str
	if feedback_content!="":
		context['status'] = 'completed'
	else:
		context['status'] = 'pending'

	print("Context: ", context)

	if task_name == 'summ':
		return render(request, 'tasks/evaluation/feedbacks.html', context)
	else:
		return render(request, 'tasks/404.html')


@csrf_exempt
def save_feedback(request):
	feedbacks_json_path = 'static/feedbacks/final_feedbacks.jsonl'
	task_name = 'summ'

	if debug:
		print("Json Path: ", feedbacks_json_path, "\tTaskName: ", task_name)

	if task_name == 'summ':
		if debug:
			print("POST Request: ", request.POST)

		file_name = str(request.POST.get('file_name', ''))
		feedback_content = str(request.POST.get('feedback', ''))
		
		feedbacks = []
		if os.path.exists(feedbacks_json_path):
			feedbacks = read_feedbacks(feedbacks_json_path)

		update_status = False
		for i in range(len(feedbacks)):
			entry = feedbacks[i]
			if str(entry.get('file_name', ''))==file_name:
				feedbacks[i]['content'] = feedback_content
				update_status = True
				break
		
		if not update_status:
			feedbacks.append({'file_name': file_name, 'content': feedback_content})
		
		save_status = write_feedbacks(feedbacks_json_path, feedbacks)
		if save_status:
			return JsonResponse({'message': 'Feedback Saved Successfully!', 'status': 'success'})
		else:
			return JsonResponse({'message': 'Error while saving feedback...!', 'status': 'error'})


@csrf_exempt
def find_next_id(request):
	
	task_name = request.POST.get('task_name', '')
	if task_name=='':
		task_name = 'summ'

	current_id = request.POST.get('current_id', '')
	next_id = request.POST.get('next_id', '')

	json_path = request.session.get('json_path', '')
	if json_path!="" and path.exists(json_path):
		if next_id=='':
			ids_dict = read_jsonl(json_path, return_ids=True)

			## Find the next article id based on the completion status/ mark for review in headline / current id
			for entry in ids_dict:
				if (current_id!='' and current_id==str(entry['id'])) or (entry.get('eval_status', '')=='completed'):
					continue

				next_id = str(entry['id'])
				break

		if debug:
			print("Current ID: ", current_id, "\tNext ID: ", next_id)

		context = {}

		data = read_jsonl(json_path, filter_ids=[next_id])
		context['articles'] = read_jsonl(json_path, return_ids=True)
		if len(data)>0:
			data = data[0]
		
		
		if len(data)==0:
			data = {}

		entry_data = {}
		if task_name == 'summ':
			for key in SUMMARIZATION_LABELS:
				if key not in data:
					if key=='evaluation':
						data[key] = {}
					else:
						data[key] = ''

			article = ''
			summary = ''
			title = ''

			### Fetching the article contents
			if data.get('sent_article', '')=='':
				if data.get('checked_article')=='':
					article = data.get('text', '')
				else:
					article = data.get('checked_article')
				
				if article!='':
					article = sentencify(article)
				else:
					article = 'Empty Article'
			else:
				article = data.get('sent_article')

			### Fetching the summary contents
			if data.get('sent_summary', '')=='':
				if data.get('summary', '')=='':
					summary = ''
				else:
					summary = data.get('summary', '')
				
				if summary!='':
					summary = sentencify(summary)
				else:
					summary = 'Empty Summary'
			else:
				summary = data.get('sent_summary', '')

			### Fetching the title contents
			title = data.get('title', '')

			evaluation_data = data.get('evaluation', '')
			if evaluation_data=='':
				evaluation_data = {}

			if debug:
				print("Evaluation Data: ", evaluation_data)

			relevance = evaluation_data.get('relevance_score', '')
			readability = evaluation_data.get('readability_score', '')
			coverage = evaluation_data.get('coverage_score', '')

			relevance_level_1 = evaluation_data.get('relevance_level_1', '')
			relevance_level_2 = evaluation_data.get('relevance_level_2', '')
			relevance_level_3 = evaluation_data.get('relevance_level_3', '')

			readability_level_1 = evaluation_data.get('readability_level_1', '')
			readability_level_2 = evaluation_data.get('readability_level_2', '')
			readability_level_3 = evaluation_data.get('readability_level_3', '')

			coverage_level_1 = evaluation_data.get('coverage_level_1', '')

			sent_article_check = evaluation_data.get('art_sent_check', 'true')
			sent_summary_check = evaluation_data.get('summ_sent_check', 'true')

			text_comments = evaluation_data.get('text_comments', '')

			entry_data['id'] = data.get('id', '')
			entry_data['wb_display'] = data.get('wb_display', '')
			entry_data['article'] = article
			entry_data['summary'] = summary
			entry_data['title'] = title
			entry_data['relevance_score'] = relevance
			entry_data['readability_score'] = readability
			entry_data['coverage_score'] = coverage
			entry_data['relevance_level_1'] = relevance_level_1
			entry_data['relevance_level_2'] = relevance_level_2
			entry_data['relevance_level_3'] = relevance_level_3
			entry_data['readability_level_1'] = readability_level_1
			entry_data['readability_level_2'] = readability_level_2
			entry_data['readability_level_3'] = readability_level_3
			entry_data['coverage_level_1'] = coverage_level_1
			entry_data['art_sent_check'] = sent_article_check
			entry_data['summ_sent_check'] = sent_summary_check
			entry_data['text_comments'] = text_comments

		context['entry_data'] = entry_data

		if debug:
			print("Context: ", context)
			
		return JsonResponse(context)


@csrf_exempt
def save_contents(request):

	json_path = request.session.get('json_path', '')
	task_name = 'summ'

	if debug:
		print("Json Path: ", json_path, "\tTaskName: ", task_name)

	if task_name == 'summ':
		if debug:
			print("POST Request: ", request.POST)

		current_id = str(request.POST.get('current_id', ''))
		eval_data = {}
		eval_data['relevance_score'] = request.POST.get('relevance_score')
		eval_data['readability_score'] = request.POST.get('readability_score')
		eval_data['coverage_score'] = request.POST.get('coverage_score')

		eval_data['relevance_level_1'] = request.POST.get('relevance_level_1')
		eval_data['relevance_level_2'] = request.POST.get('relevance_level_2')
		eval_data['relevance_level_3'] = request.POST.get('relevance_level_3')

		eval_data['readability_level_1'] = request.POST.get('readability_level_1')
		eval_data['readability_level_2'] = request.POST.get('readability_level_2')
		eval_data['readability_level_3'] = request.POST.get('readability_level_3')

		eval_data['coverage_level_1'] = request.POST.get('coverage_level_1')

		eval_data['art_sent_check'] = request.POST.get('art_sent_check')
		eval_data['summ_sent_check'] = request.POST.get('summ_sent_check')

		eval_data['text_comments'] = request.POST.get('text_comments')
		
		if debug:
			print("Evaluation Data (save): ", eval_data)

		return save_summ_contents(current_id, eval_data, json_path)
	else:
		return JsonResponse({'status': 'error', 'message': 'Task name not specified...Refresh the page and try again!', 'next_article': {}})



### =========================== xxx =====================================
###					Summarization functions
### =========================== xxx =====================================
@csrf_exempt
def sentenciy_text(request):
	text = request.POST.get('text', '')

	sentencified_text = ""
	if text!="":
		sentencified_text = sentencify(text)
	
	return JsonResponse({'sent_text': sentencified_text})


def save_summ_contents(current_id, eval_data, json_path):
	if debug:
		print("Eval Data (save): ", eval_data)
	if current_id!="" and path.exists(json_path) and len(eval_data)>0:
		update_status = False

		### Read the json data
		data = read_jsonl(json_path)

		### Update the label contents into the json data
		completion_status = False
		comments = ''
		for i in range(len(data)):
			if current_id == data[i]['id']:
				article_contents = data[i]
				data[i]['evaluation'] = eval_data
				
				completion_status = annotation_status(data[i])
				print("Completion Status: ", str(completion_status))
				if completion_status:
					data[i]['eval_status'] = 'completed'
				else:
					comments += "Annotation not completed...!"
				update_status = True
				break
		
		
		if len(comments)==0:
			### Save the json data
			status = write_as_jsonl(json_path, data)
			
			if status:
				if update_status:
					message = 'evaluations saved successfully'
					return JsonResponse({'status': 'success', 'message': message, 'completed': str(completion_status)})
				else:
					return JsonResponse({'status': 'warning', 'message': 'Error while saving contents', 'completed': str(completion_status)})
			else:
				return JsonResponse({'status': 'warning', 'message': 'Error while writing contents to file', 'completed': str(completion_status)})
		else:
			return JsonResponse({'status': 'error', 'message': comments, 'completed': str(completion_status)})
	else:
		return JsonResponse({'status': 'warning', 'message': 'Invalid parameters...!', 'completed': str(completion_status)})