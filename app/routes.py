from flask import Blueprint, jsonify, abort, make_response, request
from app.models.task import Task
from app.models.goal import Goal
from app import db
from datetime import datetime
import requests
import os

tasks_bp = Blueprint('tasks', __name__, url_prefix='/tasks')
slack_path = 'https://slack.com/api/chat.postMessage'

def send_slack_notification(task):
    headers = {'Authorization': f'Bearer {os.environ.get("SLACK_API_KEY")}'}
    
    query_param = {
        'channel': 'task-notifications',
        'text': f'Someone just completed {task}!'
        # 'format': 'json', do we need this line?
    }

    return requests.post(slack_path, params=query_param, headers=headers)  

def validate_task(task_id):
    #this portion makes sure the input type is valid
    try:
        task_id = int(task_id)
    except ValueError:
        abort(make_response({'details': 'Invalid id. ID must be an integer.'}, 400))
    task = Task.query.get(task_id)

    #this portion handles whether task record exists
    if not task:
        abort(make_response({'details': 'Task id not found.'}, 404))

    return task    

def task_response(task):
    is_complete = False
    if task.completed_at:
        is_complete = True

    response_dict = {'task':
            {'id': task.task_id,
            'title': task.title,
            'description': task.description,
            'is_complete': is_complete}
        }
    if task.goal_id:
        response_dict['task']['goal_id'] = task.goal_id
    return jsonify(response_dict)

@tasks_bp.route('', methods=['GET'])
def get_tasks():
    query_params = request.args
    if 'sort' in query_params:
        sort_order = request.args.get('sort')
        if sort_order == 'asc':
            tasks = Task.query.order_by(Task.title.asc())
        elif sort_order == 'desc':
            tasks = Task.query.order_by(Task.title.desc())
    else:
        tasks = Task.query.all()
    tasks_response = []
    
    for task in tasks:
        is_complete = False
        if task.completed_at:
            is_complete = True
        tasks_response.append({
            "id": task.task_id,
            "title": task.title,
            "description": task.description,
            "is_complete": is_complete
        })
    return jsonify(tasks_response)

@tasks_bp.route('', methods=['POST'])
def create_task():
    request_body = request.get_json() #turns request body into python dictionary
    if 'title' not in request_body or\
        'description' not in request_body:
        return jsonify({'details': 'Invalid data'}), 400
    
    new_task = Task(title=request_body['title'], 
                    description=request_body['description'])
    
    if 'completed_at' in request_body:
        new_task.completed_at=datetime.utcnow()
    
    db.session.add(new_task)
    db.session.commit()

    return task_response(new_task), 201

@tasks_bp.route('/<task_id>', methods=['DELETE', 'PUT', 'GET'])
def handle_one_task(task_id):
    task = validate_task(task_id)
    response_body = task_response(task)
    if request.method == 'DELETE':
        task = validate_task(task_id)

        response_body = jsonify({
            'details': f'Task {task_id} "{task.title}" successfully deleted'
        }), 200
        db.session.delete(task)
    elif request.method == 'PUT':
        request_body = request.get_json()

        if 'title' not in request_body or\
            'description' not in request_body:
            return jsonify({'msg': f'Request must include title and description'}), 400

        task.title = request_body['title']
        task.description = request_body['description']

        if 'completed_at' in request_body:
            task.completed_at = datetime.utcnow()

        response_body = task_response(task)
    elif request.method == 'GET':
        return response_body

    db.session.commit()
    return response_body


@tasks_bp.route('/<task_id>/mark_complete', methods=['PATCH'])
def mark_complete(task_id):
    task = validate_task(task_id)
    
    task.completed_at = datetime.utcnow()

    db.session.commit()
    send_slack_notification(task.title)
    return task_response(task)

@tasks_bp.route('/<task_id>/mark_incomplete', methods=['PATCH'])
def mark_incomplete(task_id):
    task = validate_task(task_id)

    task.completed_at = None

    db.session.commit()

    return task_response(task)

goals_bp = Blueprint('goals', __name__, url_prefix='/goals')

def validate_goal(goal_id):
    try:
        goal_id = int(goal_id)
    except ValueError:
        abort(make_response({'details': 'Invalid id. ID must be an integer.'}, 400))
    goal = Goal.query.get(goal_id)

    if not goal:
        abort(make_response({'details': 'goal id not found.'}, 404))

    return goal

def goal_response(goal):
    return {
        'id': goal.goal_id,
        'title': goal.title
    }

@goals_bp.route('', methods=['GET'])
def get_goals():
    goals = Goal.query.all()
    goals_response = []

    for goal in goals:
        goals_response.append(goal_response(goal))
    
    return jsonify(goals_response)

@goals_bp.route('', methods=['POST'])
def create_goal():
    request_body = request.get_json()

    if 'title' not in request_body:
        abort(make_response({"details": "Invalid data"}, 400))

    new_goal = Goal(title=request_body['title'])

    db.session.add(new_goal)
    db.session.commit()

    return {'goal': goal_response(new_goal)}, 201

@goals_bp.route('/<goal_id>', methods=['DELETE', 'PUT', 'GET'])
def handle_one_goal(goal_id):
    goal = validate_goal(goal_id)
    response_body = {'goal': goal_response(goal)}

    if request.method == 'DELETE':
        response_body = jsonify({
        'details': f'Goal {goal_id} "{goal.title}" successfully deleted'
        })
        db.session.delete(goal)
        
    elif request.method == 'PUT':
        request_body = request.get_json()
        goal.title = request_body['title']
        response_body = {'goal': goal_response(goal)}
    
    elif request.method == 'GET':
        return response_body
        
    db.session.commit()
    return response_body

@goals_bp.route('/<goal_id>/tasks', methods=['POST'])
def create_task_for_goal(goal_id):
    goal = validate_goal(goal_id)
    request_body = request.get_json()
    task_ids = request_body['task_ids']
    
    for task_id in task_ids:   
        task = Task.query.get(task_id)
        task.goal_id = goal.goal_id
        
    db.session.commit()

    return {
        'id': goal.goal_id,
        'task_ids': request_body['task_ids']
        }

@goals_bp.route('/<goal_id>/tasks', methods=['GET'])
def get_tasks_for_goal(goal_id):
    goal = validate_goal(goal_id)
    tasks_response = []
    for task in goal.tasks:
        is_complete = False
        if task.completed_at:
            is_complete = True
        tasks_response.append({
            "id": task.task_id,
            "goal_id": task.goal_id,
            "title": task.title,
            "description": task.description,
            "is_complete": is_complete
        })
    
    return {
        'id': goal.goal_id,
        'title': goal.title,
        'tasks': tasks_response
        }

