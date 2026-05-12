from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from models import Linkages
from extension import db

import logging

logging.basicConfig(level=logging.DEBUG)
# Define the Blueprint
Linkages_bp = Blueprint('linkages', __name__, template_folder='templates')

@Linkages_bp.route('/linklist', methods=['GET'])
def linklist():
    # Query the database for all linkages
    list_link = Linkages.query.all()
    numLocal = Linkages.query.filter_by(coverage=0).count()
    numForeign = Linkages.query.filter_by(coverage=1).count()

    print(numLocal)
    # Render the template with the queried data
    return render_template('linkages/linkages.html', list_link=list_link, numLocal=numLocal, numForeign=numForeign)


@Linkages_bp.route('/add_linkage', methods=['POST'])
def add_linkage():
    try:
        name = request.form['linkname']
        coverage = int(request.form['coverage'])
        address = request.form['linkaddress']

        logging.debug(f'name: {name}, coverage: {coverage}, address: {address}')

        new_linkage = Linkages(name=name, address=address, coverage=coverage)

        db.session.add(new_linkage)
        db.session.commit()
        logging.info('New Library Linkage added successfully')
        return jsonify({'message': 'New Library Linkage added successfully'}), 200
    except Exception as e:
        db.session.rollback()
        logging.error(f'Error adding new linkage: {str(e)}')
        return jsonify({'message': f'Error adding linkage: {str(e)}'}), 500

@Linkages_bp.route('/filter_linkages', methods=['GET'])
def filter_linkages():
    coverage = request.args.get('coverage', type=int)  # Optional filter
    query = Linkages.query
    if coverage is not None:
        query = query.filter_by(coverage=coverage)
    data = [{'id': l.id, 'name': l.name, 'address': l.address, 'coverage': l.coverage} for l in query.all()]
    return jsonify({'data': data})


@Linkages_bp.route('/edit_linkage', methods=['POST'])
def edit_linkage():
    linkage_id = request.form['id']
    name = request.form['linkname']
    address = request.form['linkaddress']
    coverage = int(request.form['coverage'])
    
    linkage = linkage.query.get(linkage_id)
    if linkage:
        linkage.name = name
        linkage.address = address
        linkage.coverage = coverage
        db.session.commit()
        return jsonify({'message': 'Linkage updated successfully!'})
    return jsonify({'message': 'Linkage not found.'}), 404
