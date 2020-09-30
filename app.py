import config
import requests
import json
import maya
from maya import MayaInterval
from types import SimpleNamespace
from datetime import datetime
from jira import JIRA
from requests.auth import HTTPBasicAuth

def get_issues_by_jql():    
    pagination_start_at = 0
    pagination_max_results = 100
    pagination_total = 9999999

    options = {"server": config.jira_base_url}
    jira = JIRA(basic_auth=(config.jira_user, config.jira_api_key), options=options)
    issues = {}
    while pagination_total > pagination_start_at:                
        if pagination_start_at > 100:        
            pagination_start_at = pagination_total + 10
        
        issues = jira.search_issues(f"project = {config.jira_project}" , maxResults=pagination_max_results, startAt=pagination_start_at)
        for issue in issues:
            print(issue.key)
            print(issue.fields.created)
            changelog = get_issue_changelog(issue.key)
            issue.changelog = changelog
            issue.time_in_status = get_issue_time_in_status(issue)
            issue.cycleTime = sum_time_in_statuses(issue.time_in_status, config.cycle_time_status_to_consider)
            issue.leadTime = sum_time_in_statuses(issue.time_in_status, config.lead_time_status_to_consider)
            issue.waitingTime = sum_time_in_statuses(issue.time_in_status, config.waiting_status)            
            #TODO: Recuperar quantidade de subtasks(filhos) de uma issue
            
        pagination_start_at += pagination_max_results
        pagination_max_results = issues.maxResults
        pagination_total = issues.total
    return issues

def get_issue_changelog(issue_key): 
    response = requests.get(f'{config.jira_base_url}/rest/api/latest/issue/{issue_key}?expand=changelog', auth=HTTPBasicAuth(config.jira_user, config.jira_api_key))
    response_object = json.loads(response.text, object_hook=lambda d: SimpleNamespace(**d))
    return response_object.changelog

def get_issue_time_in_status(issue):
    statuses = {}
    changelog = issue.changelog
    previous_status = config.jira_initial_status.upper()        
    now = maya.now()
    created = maya.parse(issue.fields.created)    
    event = MayaInterval(start=created, end=now)
    statuses[previous_status] = event.duration / config.default_time_scale 
    previous_status_change_date = created

    i = len(changelog.histories)
    while i > 0:
        history = changelog.histories[i-1]        
        j = 0
        while j < len(history.items):
            item = history.items[j]            
            if item.field == 'status':
                status = item.fromString.upper()            
                if not status in statuses:
                    statuses[status] = 0
                status_change_date = maya.parse(history.created)
                interval = MayaInterval(start=previous_status_change_date, end=status_change_date)
                duration = interval.duration / config.default_time_scale 
                statuses[status] += duration
                previous_status_change_date = status_change_date
                previous_status = item.toString
            j += 1
        i -= 1
    return statuses

def sum_time_in_statuses(time_in_status, statuses_to_sum): 
    time = 0
    for status in statuses_to_sum:
        if status in time_in_status:
            time += time_in_status[status]    
    return time

get_issues_by_jql()