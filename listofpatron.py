import os
from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
from models import db, User 

# Define the Blueprint with the correct name
# The name 'listofUser' must match the name used in url_for('listofUser.lisofPatron')
listofUser_bp= Blueprint('listofUser_bp',__name__)


@listofUser_bp.route('/lisofPatron')
def lisofPatron():
    """
    Renders the list of patrons.
    """
    patron_List= User.query.all()
    
    return render_template('patron/patron.html', patron_List=patron_List)
