from bs4 import BeautifulSoup
import inspect
import json
import os
from os.path import abspath, dirname, isdir, isfile, join, relpath
import re
from scrape_liferay import get_liferay_content, get_namespaced_parameters
import sys
import webbrowser

sys.path.insert(0, dirname(dirname(abspath(inspect.getfile(inspect.currentframe())))))

from getparent import getparent
import git
from git import git_root, current_branch

base_tag = getparent(True)

def get_baseline_id():
	with open(join(dirname(sys.argv[0]), 'patcher.json'), 'r') as file:
		patcher_json = json.load(file)
		return patcher_json[base_tag]

def get_fix_id(workaround=False):
	base_url = 'https://patcher.liferay.com/group/guest/patching/-/osb_patcher'
	fix_name = get_fix_name()

	parameters = {
		'advancedSearch': 'true',
		'patcherProjectVersionIdFilter': get_baseline_id(),
		'patcherFixName': fix_name,
		'hideOldFixVersions': 'true',
		'typeFilter': '1' if workaround else 0,
		'andOperator': 'true'
	}

	namespaced_parameters = get_namespaced_parameters('1_WAR_osbpatcherportlet', parameters)

	fix_html = get_liferay_content(base_url, namespaced_parameters)
	soup = BeautifulSoup(fix_html, 'html.parser')

	search_container = soup.find('div', {'id': '_1_WAR_osbpatcherportlet_patcherFixsSearchContainerSearchContainer'})

	if search_container is None:
		return None

	table = search_container.find('table')

	if table is None:
		return None

	thead = table.find('thead')
	tbody = table.find('tbody')

	if thead is None or tbody is None:
		return None

	fix_id_index = 0
	content_index = 0

	for i, th in enumerate(thead.find_all('th')):
		th_text = th.text.strip().lower()

		if th_text == 'fix id':
			fix_id_index = i
		elif th_text == 'content':
			content_index = i

	for tr in tbody.find_all('tr'):
		cells = tr.find_all('td')

		if cells is not None and cells[content_index] is not None and fix_name == cells[content_index].text.strip():
			return cells[fix_id_index].text.strip()

	return None

def get_fix_name():
	pattern = re.compile('LP[EPS]-[0-9]*')

	if current_branch.find('LPE-') == 0 or current_branch.find('LPP-') == 0 or current_branch.find('LPS-') == 0:
		return ','.join(sorted(pattern.findall(current_branch)))

	fixes = set()

	for line in git.log('%s..%s' % (base_tag, 'HEAD'), '--pretty=%s').split('\n'):
		fixes.update(pattern.findall(line))

	return ','.join(sorted(fixes))

def open_patcher_portal():
	print('Checking patcher portal for existing fix...')

	fix_id = get_fix_id()

	if fix_id is None:
		fix_id = get_fix_id(True)

	if fix_id is None:
		print('No existing fix to update, opening window for a new fix...')
		base_url = 'https://patcher.liferay.com/group/guest/patching/-/osb_patcher/fixes/create'
	else:
		print('Opening window to update fix %s...' % fix_id)
		base_url = 'https://patcher.liferay.com/group/guest/patching/-/osb_patcher/fixes/%s/edit' % fix_id

	if base_tag.find('fix-pack-base-6130') == 0 or base_tag.find('fix-pack-base-6210') == 0:
		product_version = 1
	else:
		product_version = 2

	origin_name = sys.argv[1]

	parameters = {
		'productVersion': product_version,
		'patcherProjectVersionId': get_baseline_id(),
		'committish': current_branch,
		'patcherFixName': get_fix_name(),
		'gitRemoteURL': origin_name
	}

	namespaced_parameters = get_namespaced_parameters('1_WAR_osbpatcherportlet', parameters)

	query_string = '&'.join(['%s=%s' % (key, value) for key, value in namespaced_parameters.items()])
	webbrowser.open_new_tab('%s?%s' % (base_url, query_string))

if __name__ == '__main__':
	open_patcher_portal()