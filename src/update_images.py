import logging
import sys

from oslo_config import cfg
import requests
import yaml

from bs4 import BeautifulSoup
import re

PROJECT_NAME = 'images'
CONF = cfg.CONF
opts = [
    cfg.BoolOpt('debug', help='Enable debug logging', default=False),
    cfg.StrOpt('images', help='Path to the images.yml file', default='etc/images.yml'),
    cfg.StrOpt('new_images', help='Path to the images.yml file', default='etc/images.yml'),
    cfg.StrOpt('supported_images', help='Path to the images.yml file', default='etc/supported_images.yml'),
]
CONF.register_cli_opts(opts)
CONF(sys.argv[1:], project=PROJECT_NAME)

if CONF.debug:
    level = logging.DEBUG
else:
    level = logging.INFO
logging.basicConfig(format='%(asctime)s - %(message)s', level=level, datefmt='%Y-%m-%d %H:%M:%S')


def get_daily_build(build_name):
    return re.search(r'\d{8}', build_name).group(0)


def build_url(image_name, version):
    if image_name == 'Ubuntu 20.04':
        return supported_images[image_name]['base_url'] + version + '/focal-server-cloudimg-amd64.img'
    if image_name == 'Ubuntu 18.04':
        return supported_images[image_name]['base_url'] + version + '/bionic-server-cloudimg-amd64.img'
    if image_name == 'CentOS 8':
        return supported_images[image_name]['base_url'] + version
    if 'Debian' in image_name:
        return supported_images[image_name]['base_url'] + version + 'debian-' \
               + version.rstrip('/') + '-openstack-amd64.qcow2'


def check_versions(image, versions):
    page = requests.get(image['base_url'])
    soup = BeautifulSoup(page.content, 'html.parser')
    new_versions = {}
    regex = re.compile(image['regex'])
    if soup.find('table'):
        rows = soup.find_all('tr')
        data = []
        for row in rows:
            cols = row.find_all('td')
            cols = [ele.text.strip() for ele in cols]
            if cols:
                data.append([ele for ele in cols if ele])
        for date in data:
            if re.search(image['regex'], date[0]):
                daily_build_version = ''.join(re.search(r'(\d{4})-(\d\d)-(\d\d)', date[1]).groups())
                version = date[0]
                if daily_build_version not in versions and int(daily_build_version) > int(versions[-1]):
                    new_versions[daily_build_version] = {}
                    new_versions[daily_build_version]['version'] = version
                    if image['os_version']:
                        os_version = regex.search(date[0])
                        if os_version:
                            new_versions[daily_build_version]['os_version'] = os_version.group(0)
                        else:
                            raise ValueError("Could not retrieve OS version of the image version")
    else:
        versions_on_url = set()
        for link in soup.find_all('a'):
            if re.search(image['regex'], link.get('href')):
                versions_on_url.add(regex.search(link.get('href')).group(0))
        versions_on_url = sorted(versions_on_url)
        for version in versions_on_url:
            daily_build_version = get_daily_build(version)
            if daily_build_version not in versions and int(daily_build_version) > int(versions[-1]):
                new_versions[daily_build_version] = {}
                new_versions[daily_build_version]['version'] = version
    return new_versions


with open(CONF.images) as fp:
    data = yaml.load(fp, Loader=yaml.SafeLoader)
    images = data.get('images', [])

with open(CONF.supported_images) as fp:
    supported_images = yaml.load(fp, Loader=yaml.SafeLoader)

for image in images:
    versions = dict()
    version_list = []
    for version in image['versions']:
        versions[str(version['version'])] = {
            'url': version['url']
        }
        version_list.append(version['version'])

        if 'os_version' in version:
            versions[version['version']]['os_version'] = version['os_version']

    if image['name'] in supported_images:
        newer_versions = check_versions(supported_images[image['name']], version_list)
        if newer_versions:
            for version in newer_versions:
                include_version = {'version': version,
                                   'url': build_url(image['name'], newer_versions[version]['version'])}
                if supported_images[image['name']]['os_version']:
                    include_version['os_version'] = newer_versions[version]['os_version']

                image['versions'].append(include_version)

with open(CONF.new_images, "w") as fp:
    yaml.dump({"images": images}, fp)
