"""Persistent model choices shared by API workers; changing a choice starts no work."""
import os
from sqlalchemy import Column, MetaData, String, Table, select
from sqlalchemy.dialects.postgresql import insert

OPTIONS = [
    {'id': 'gpt-6-luna', 'label': 'gpt-6-luna — oszczędny'},
    {'id': 'gpt-6.1-terra', 'label': 'gpt-6.1-terra'},
    {'id': 'gpt-6.1-sol', 'label': 'gpt-6.1-sol'},
    {'id': 'gpt-6-astra', 'label': 'gpt-6-astra — najdroższy'},
]
DEFAULTS = {'contacts': ('OPENAI_CONTACT_MODEL', 'gpt-6-luna'),
            'region': ('OPENAI_RESEARCH_MODEL', 'gpt-6-luna'),
            'planner': ('OPENAI_PLANNER_MODEL', 'gpt-6.1-terra')}
metadata = MetaData()
settings = Table('admin_task_models', metadata,
                 Column('task', String(20), primary_key=True),
                 Column('model', String(80), nullable=False))
archived = Table('admin_archived_tasks', metadata,
                 Column('task', String(80), primary_key=True))
_engine = None


def initialize(engine):
    global _engine
    metadata.create_all(engine)
    _engine = engine


def model(kind):
    if _engine is not None:
        with _engine.connect() as connection:
            saved = connection.scalar(select(settings.c.model).where(settings.c.task == kind))
        if saved:
            return saved
    variable, default = DEFAULTS[kind]
    return os.environ.get(variable, os.environ.get('OPENAI_MODEL', default))


def save(kind, selected):
    if kind not in DEFAULTS or selected not in {item['id'] for item in OPTIONS}:
        raise ValueError('Nieobsługiwany model lub zadanie.')
    with _engine.begin() as connection:
        statement = insert(settings).values(task=kind, model=selected)
        connection.execute(statement.on_conflict_do_update(index_elements=['task'], set_={'model': selected}))


def task_key(kind, region='lubuskie'):
    return f'region:{region}' if kind == 'region' else kind


def archived_tasks():
    with _engine.connect() as connection:
        return set(connection.scalars(select(archived.c.task)))


def archive(kind, region='lubuskie'):
    with _engine.begin() as connection:
        connection.execute(insert(archived).values(task=task_key(kind,region)).on_conflict_do_nothing())


def restore(region='lubuskie'):
    with _engine.begin() as connection:
        connection.execute(archived.delete().where(archived.c.task.in_(['photos','contacts',task_key('region',region)])))
