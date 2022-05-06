from flask import Blueprint, jsonify, abort, make_response, request
from app.models.task import Task
from app import db

tasks_bp = Blueprint('tasks', __name__, url_prefix='/tasks')

def validate_task(task_id):
    #this portion makes sure the input type is valid
    try:
        task_id = int(task_id)
    except ValueError:
        abort(make_response({'details': f'Invalid id. ID must be an integer.'}, 400))
    task = Task.query.get(task_id)

    #this portion handles whether task record exists
    if not task:
        abort(make_response({'details': f'Task id not found.'}, 404))

    return task    

def task_response(task):
    is_complete = False
    if task.completed_at:
        is_complete = True

    return jsonify({'task':
        {'id': task.task_id,
        'title': task.title,
        'description': task.description,
        'is_complete': is_complete}
    })

@tasks_bp.route('', methods=['GET'])
def handle_tasks():
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

@tasks_bp.route('/<task_id>', methods=['GET'])
def get_one_task(task_id):
    task = validate_task(task_id)

    return task_response(task)

@tasks_bp.route('', methods=['POST'])
def create_task():
    request_body = request.get_json() #turns request body into python dictionary
    if 'title' not in request_body or\
        'description' not in request_body:
        return jsonify({'details': 'Invalid data'}), 400
    
    new_task = Task(title=request_body['title'], 
                    description=request_body['description'])
    
    db.session.add(new_task)
    db.session.commit()
    
    response_body = task_response(new_task)

    return response_body, 201

@tasks_bp.route('/<task_id>', methods=['PUT'])
def update_task(task_id):
    task = validate_task(task_id)
    request_body = request.get_json()

    if 'title' not in request_body or\
        'description' not in request_body:
        return jsonify({'msg': f'Request must include title and description'}), 400

    task.title = request_body['title']
    task.description = request_body['description']

    db.session.commit()

    return task_response(task)

@tasks_bp.route('/<task_id>', methods=['DELETE'])
def delete_one_task(task_id):
    task = validate_task(task_id)

    response_body = jsonify({
        'details': f'Task {task_id} "{task.title}" successfully deleted'
    })
    db.session.delete(task)
    db.session.commit()


    return response_body, 200