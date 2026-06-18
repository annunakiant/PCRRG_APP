from flask import Blueprint
plus_bp = Blueprint('plus', __name__, template_folder='../templates')
from .ui import *  # noqa
