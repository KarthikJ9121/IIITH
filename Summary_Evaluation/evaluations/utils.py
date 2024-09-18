from os import path, listdir, stat
import json
import numpy as np
from TeluguTokenizer.summ_quality_check import *

debug = False

SUMM_CRITERIA = {
    "abs0" : [30, 80],
    "compression" : [60, 80],
    "has_prefix" : "False"
}

SUMMARIZATION_EVAL_LABELS = ["relevance_score", "readability_score", "coverage_score", "relevance_level_1", "relevance_level_2", "relevance_level_3", "readability_level_1", "readability_level_2", "readability_level_3", "coverage_level_1", "art_sent_check", "summ_sent_check", "text_comments"]

SUMMARIZATION_LABELS = ["text", "checked_article", "sent_article", "summary", "sent_summary", "title", "section", "evaluation"]


# Read a jsonl file into list-of-dictionaries
def read_jsonl(filename, return_ids=False, filter_ids=[]):
    entries = []
    
    with open(filename, 'r', encoding='utf-8') as fp:
        for line in fp.readlines():
            line = line.strip().replace('\n', '').replace('\r', '')
            line = json.loads(line)
            if len(filter_ids)==0 or str(line['id']) in filter_ids:
                section_name = line.get('section', '-1')
                section_id = '-1'
                if section_name == "first":
                    section_id = '1'
                elif section_name == "second":
                    section_id = '2'
                elif section_name == "third":
                    section_id = '3'


                if return_ids:                
                    entries.append({'wb_display': line['wb_display'], 'id': line['id'], 'status': line.get('status', ''), 'section_id': section_id, 'eval_status': line.get('eval_status', '')})
                else:
                    line['section_id'] = section_id
                    entries.append(line)
        
    return entries


# Read a jsonl file and include only the evaluated samples.
def read_evaluated_comments(filename):
    entries = []

    overall_feedback = ""
    with open(filename, 'r', encoding='utf-8') as fp:
        for line in fp.readlines():
            line = line.strip().replace('\n', '').replace('\r', '')
            line = json.loads(line)
            if 'evaluation' in line:
                evaluation = line.get('evaluation', {})
                scores = "Relevance: " + str(evaluation.get('relevance_score', '#N/A')) + "\t"
                scores += "Readability: " + str(evaluation.get('readability_score', '#N/A')) + "\t"
                scores += "Coverage: " + str(evaluation.get('coverage_score', '#N/A'))

                relevance_comments = ""
                if str(evaluation.get('relevance_level_1', ''))!='':
                    relevance_comments += str(evaluation.get('relevance_level_1', '')) + "\n"
                if str(evaluation.get('relevance_level_2', ''))!='':
                    relevance_comments += str(evaluation.get('relevance_level_1', '')) + "\n"
                if str(evaluation.get('relevance_level_3', ''))!='':
                    relevance_comments += str(evaluation.get('relevance_level_1', '')) + "\n"
                
                readability_comments = ""
                if str(evaluation.get('readability_level_1', ''))!='':
                    readability_comments += str(evaluation.get('readability_level_1', '')) + "\n"
                if str(evaluation.get('readability_level_2', ''))!='':
                    readability_comments += str(evaluation.get('readability_level_2', '')) + "\n"
                if str(evaluation.get('readability_level_3', ''))!='':
                    readability_comments += str(evaluation.get('readability_level_3', '')) + "\n"

                coverage_comments = ""
                if str(evaluation.get('coverage_level_1', ''))!='':
                    coverage_comments += str(evaluation.get('coverage_level_1', ''))
                
                text_comments = ""
                if str(evaluation.get('text_comments', ''))!='':
                    text_comments += str(evaluation.get('text_comments', ''))

                if text_comments!="":
                    overall_feedback += "In Article-" + str(line.get('wb_display', '')) + ", " + text_comments +"\n"
                

                entries.append({'scores': scores, 'relevance_comments': relevance_comments, 'readability_comments': readability_comments, 'coverage_comments': coverage_comments, 'text_comments': text_comments, 'id': line.get('id', ''), 'wb_display': line.get('wb_display', '')})

    overall_feedback = overall_feedback.replace(r'\n+', '\n').replace(r'[ ]+', ' ').replace(r'\t+', ' ').replace(r'\r+', ' ').strip()
    return entries, overall_feedback


# Read a jsonl file with the feedbacks
def read_feedbacks(filename):
    entries = []
    
    with open(filename, 'r', encoding='utf-8') as fp:
        for line in fp.readlines():
            line = line.strip().replace('\n', '').replace('\r', '')
            line = json.loads(line)
            entries.append(line)
        
    return entries

# Write the feedbacks into a jsonl file
def write_feedbacks(filename, jsonl_data):
    try:
        with open(filename, 'w', encoding='utf-8') as fp:
            for line in jsonl_data:
                line = json.dumps(line)
                fp.write(line + "\n")
        return True
    except Exception as e:
        print("Feedback Exception (save): ", e)
        return False


# Save list-of-dictionaries as a jsonl file
def write_as_jsonl(out_filename, listOfDicts):
    try:
        with open(out_filename, 'w', encoding='utf-8') as outfile:
            for each in listOfDicts:
                json.dump(each, outfile, ensure_ascii=False)
                outfile.write('\n')
        return True
    except:
        return False


# Load the annotation statistics
def load_annotation_stats(base_url):
    stats = []

    feedbacks_json_path = 'static/feedbacks/final_feedbacks.jsonl'
    feedbacks = []
    if path.exists(feedbacks_json_path):
        feedbacks = read_feedbacks(feedbacks_json_path)

    for file_name in listdir(base_url):
        entry  = {}

        file_base = path.basename(file_name)
        file_name_str = file_base.replace('.jsonl', '').replace('.json', '')
        file_path = path.join(base_url, file_base)

        data = read_jsonl(file_path)
        annotation_completed, evaluation_completed = get_completed(data)
        entry['no_of_samples'] = len(data)

        entry['file_name'] = file_name_str
        entry['annotation_completed'] = len(annotation_completed)
        entry['evaluation_completed'] = evaluation_completed
        entry['total_sets'] = len(evaluation_completed)
        entry['evaluation_scores'] = ''
        entry['evaluation_comments'] = ''

        eval_status = 'pending'
        flag = False
        for section_name in evaluation_completed:
            completed_eval_samples = len(evaluation_completed[section_name]['completed'])
            total_samples = len(evaluation_completed[section_name]['articles'])

            if total_samples/3 > completed_eval_samples:
                flag = True
                break
        if not flag:
            eval_status = 'completed'
        
        entry['status'] = eval_status

        feedback_status = 'pending'
        for feedback_entry in feedbacks:
            if str(feedback_entry.get('file_name'))==file_name_str:
                feedback_status = 'completed'
                break

        entry['feedback_status'] = feedback_status

        stats.append(entry)

    if debug:
        print("Stats: ", stats)
        
    return stats


def annotation_status(sample):

    if isinstance(sample, dict):
        for key in SUMMARIZATION_LABELS:
            if key not in sample:
                if debug:
                    print("Key: ", key)
                return False
        
        if debug:
            print("All labels available")
        
        checked_content = sample.get('checked_article', '')
        sentencified_content = sample.get('sent_article', '')
        if not content_validation(checked_content, sentencified_content):
            return False
        if debug:
            print("Checked article and Sentencified article contents are same")

        summary_content = sample.get('summary', '')
        summ_sentencified_content = sample.get('sent_summary', '')
        if not content_validation(summary_content, summ_sentencified_content):
            return False
        if debug:
            print("Summary contents and sentencified summary contents are same")
        
        checked_content = sample.get('checked_article', '')
        summary_content = sample.get('summary', '')

        abs_0 = get_abstractivity_score(checked_content, summary_content)
        try:
            abs_0 = float(abs_0)
            if abs_0 < SUMM_CRITERIA['abs0'][0] or abs_0 > SUMM_CRITERIA['abs0'][1]:
                return False
        except:
            return False
        
        if debug:
            print("Abstractivity-0 check passed")
        
        compression = get_compression_score(checked_content, summary_content)
        try:
            compression = float(compression)
            if compression < SUMM_CRITERIA['compression'][0] or compression > SUMM_CRITERIA['compression'][1]:
                return False
        except:
            return False
        
        if debug:
            print("Compression check passed")
        
        prefix_check = has_prefix(checked_content, summary_content)
        try:
            prefix_check = bool(prefix_check)
            # if isinstance(prefix_check, bool):
            #     print("yes", str(prefix_check))
            if str(prefix_check).title() == str(SUMM_CRITERIA['has_prefix']).title():
                if debug:
                    print("Prefix check passed")
                return True
            else:
                return False
        except:
            return False
    
    if debug:
        print("Sample is not an instance of dict")

    return False


# Get the completed articles count
def get_completed(data):
    annotation_completed = []
    evaluation_completed = {}
    for entry in data:
        check_labels = []
        check_labels = ['wb_display', 'id', 'text', 'checked_article', 'sent_article', 'summary', 'sent_summary', 'title', 'section', 'abs0', 'compression', 'has_prefix']
        if validate_entries(check_labels, entry, SUMM_CRITERIA):
            annotation_completed.append(entry['id'])

            section_name = entry.get('section', 'none')
            if section_name not in evaluation_completed:
                evaluation_completed[section_name] = {'articles': [entry['id']], 'completed': []}
            else:
                evaluation_completed[section_name]['articles'].append(entry['id'])

            if entry.get('eval_status', '') == 'completed':
                if section_name not in evaluation_completed:
                    evaluation_completed[section_name] = {'articles': [entry['id']], 'completed': [entry['id']]}
                else:
                    if "completed" not in evaluation_completed[section_name]:
                        evaluation_completed[section_name]["completed"] = [entry['id']]
                    else:
                        evaluation_completed[section_name]["completed"].append(entry['id'])
    return annotation_completed, evaluation_completed


# Check whether the labels present in the keys or not
def validate_entries(labels, entry_dict, criteria = {}):
    keys = list(entry_dict.keys())
    count = 0

    ### Checking the non empty fields
    for label in labels:
        if label in keys:
            if isinstance(entry_dict[label], str):
                if entry_dict[label]!="":
                    count += 1
            elif isinstance(entry_dict[label], list):
                if len(entry_dict[label])>0:
                    count += 1
            elif isinstance(entry_dict[label], (int, float)):
                if entry_dict[label]>=0:
                    count += 1
            else:
                print("\n\nLabel: ", label)

    if debug:
        print("ID: ", entry_dict['id'], "\tCount: ", count, "\tLen: ", len(labels))
        print("Keys: ", keys, "\tLabels: ", labels)

    if len(labels)==count:
        abs0 = entry_dict['abs0']>=criteria['abs0'][0] and entry_dict['abs0']<=criteria['abs0'][1]
        compression = entry_dict['compression']>=criteria['compression'][0] and entry_dict['compression']<=criteria['compression'][1]
        has_prefix = str(entry_dict['has_prefix']).title()==str(criteria['has_prefix']).title()

        if abs0 and compression and has_prefix:
            return True
        else:   ### Summary criteria do not pass any one of the above mentioned filters
            return False

    else:       ### Non empty labels counts do not match
        return False
    

