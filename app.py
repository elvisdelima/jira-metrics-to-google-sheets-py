import config
import requests
import json
import maya
import gspread
from models.issue import Issue
from oauth2client.service_account import ServiceAccountCredentials
from maya import MayaInterval
from types import SimpleNamespace
from datetime import datetime
from jira import JIRA
from requests.auth import HTTPBasicAuth

def main():
    issues = get_issues_by_jql()
    
    headers = []    
    row = []
    for value in vars(issues[0]).items():
        if type(value[1]) not in (list, tuple, dict, set, frozenset):
            row.append(value[0])            
    headers.append(row)
    
    values = []
    for object in issues:
        row = []
        for value in vars(object).items():
            if type(value[1]) not in (list, tuple, dict, set, frozenset):
                if type(value[1]) == maya.core.MayaDT:                    
                    row.append(value[1].datetime().strftime("%Y/%m/%d-%H:%M:%S"))            
                else:
                    row.append(value[1])            
        values.append(row)
    
    update_google_sheet('Página1', headers, values)

    # page2_headers = ["Issue"]
    # page2_headers.append(config.time_in_status_status)
    
    # page2_values = []
    # for object in issues:
    #     page2_values[object.key] = object.time_in_status    

    # print(page2_headers)
    # print(page2_values)

    # update_google_sheet('Página2', page2_headers, page2_values)


def update_google_sheet(page, headers, values):
    scope = ["https://spreadsheets.google.com/feeds",'https://www.googleapis.com/auth/spreadsheets',"https://www.googleapis.com/auth/drive.file","https://www.googleapis.com/auth/drive"]    
    creds = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
    client = gspread.authorize(creds)
    worksheet = client.open_by_key(config.google_sheet_key)
    worksheet.sheet1.clear()    
    
    worksheet.values_update(page + '!A1',
        params={
            'valueInputOption': 'USER_ENTERED'
        },
        body={
            'values': headers
        })

    worksheet.values_update(page + '!A2',
        params={
            'valueInputOption': 'USER_ENTERED'
        },
        body={
            'values': values
        })
    
    # TODO: Enviar para o google sheets o time_in_status em outra aba

def get_issues_by_jql():    
    pagination_start_at = 0
    pagination_max_results = 100
    # pagination_max_results = 2
    pagination_total = 9999999

    options = {"server": config.jira_base_url}
    jira = JIRA(basic_auth=(config.jira_user, config.jira_api_key), options=options)
    issues = {}
    data = []

    while pagination_total > pagination_start_at:                        
        issues = jira.search_issues(config.jira_jql , maxResults=pagination_max_results, startAt=pagination_start_at)
        print("Total: ")
        print(issues.total)
        for item in issues:          
            changelog = get_issue_changelog(item.key)
            issue = Issue(
                item.key, 
                item.id, 
                maya.parse(item.fields.created),
                maya.parse(item.fields.resolutiondate) if item.fields.resolutiondate != None else "",                
                item.fields.issuetype.name if item.fields.issuetype != None else "", 
                item.fields.status.name,
                item.fields.summary,                 
                item.fields.assignee.displayName if item.fields.assignee != None else "",
                item.fields.assignee.raw['avatarUrls']['48x48'] if item.fields.assignee != None else "",
                item.fields.aggregatetimeoriginalestimate)

            issue.time_in_status = get_issue_time_in_status(issue, changelog)
            issue.cycle_time = sum_time_in_statuses(issue.time_in_status, config.cycle_time_status_to_consider)
            issue.lead_time = sum_time_in_statuses(issue.time_in_status, config.lead_time_status_to_consider)
            issue.waiting_time = sum_time_in_statuses(issue.time_in_status, config.waiting_status)     
            issue.child_count = get_issue_child_count(issue.key)
            data.append(issue)
            print(len(data))

        # pagination_start_at = pagination_total    
        pagination_start_at += pagination_max_results
        pagination_total = issues.total

    print(len(data))
    return data

def get_issue_child_count(issue_key):
    options = {"server": config.jira_base_url}
    jira = JIRA(basic_auth=(config.jira_user, config.jira_api_key), options=options)
    child = jira.search_issues(f"'Parent Link' = {issue_key}", maxResults=1000, startAt=0)
    return len(child)

def get_issue_changelog(issue_key): 
    response = requests.get(f'{config.jira_base_url}/rest/api/latest/issue/{issue_key}?expand=changelog', auth=HTTPBasicAuth(config.jira_user, config.jira_api_key))
    response_object = json.loads(response.text, object_hook=lambda d: SimpleNamespace(**d))
    return response_object.changelog

def get_issue_time_in_status(issue, changelog):
    statuses = {}
    previous_status = config.jira_initial_status.upper()        
    now = maya.now()
    created = maya.parse(issue.created)    
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

main()