class Issue:
  def __init__(self, key, id, created, resolution_date, type, status, summary, assignee_display_name, assignee_avatar_url, time_estimate):
    self.key = key if key != None else ""
    self.id = id if id != None else ""
    self.created = created 
    self.resolution_date = resolution_date 
    self.type = type if type != None else ""
    self.status = status if status != None else ""
    self.summary = summary if summary != None else ""
    self.assignee_display_name = assignee_display_name if assignee_display_name != None else ""
    self.assignee_avatar_url = assignee_avatar_url if assignee_avatar_url != None else ""
    self.time_estimate = time_estimate if time_estimate != None else ""
    self.time_in_status = {}
    self.cycle_time = 0.0
    self.lead_time = 0.0
    self.waiting_time = 0.0
    