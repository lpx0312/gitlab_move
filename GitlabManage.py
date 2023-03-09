#!/usr/bin/env python
# -*- coding: UTF-8 -*-
import gitlab
import json
import time
import sys
import os
import configparser
from logone import Logger
# 配置
current_dir = os.getcwd()
config = configparser.ConfigParser()
config.read('{0}/.gitlab_move.cfg'.format(current_dir), encoding='utf-8')
git_move_log_name = config.get('move-setting', 'log_path')
# 日志
logger = Logger()
git_move_log_path = '{0}/{1}'.format(current_dir,git_move_log_name)
if os.path.exists(git_move_log_path):
    old_log_name = '{0}/{1}'.format(current_dir,"".join([git_move_log_name.split('.')[0],"-"
                                                            ,time.strftime("%Y%m%d%H%M%S"),"."
                                                            ,git_move_log_name.split('.')[1]])
                                    )
    os.rename(git_move_log_path,old_log_name)
logger = logger.get_log(log_path = git_move_log_path)



def strCenter(str, len):
    import string
    lst = list(str)
    length = 0
    for item in lst:
        if item in string.printable:
            length += 1
        else:
            length += 2
    count = int((len - length) / 2)
    result = count * ' ' + str + count * ' '
    return result

def print_title(message):
    logger.info("#############################################")
    for line in message.split('+') :
        logger.info(strCenter(line,45))
    logger.info("#############################################")


# GitlabManager 类
class GitlabManage(object):
    def __init__(self, gitlab_url, user_token):
    # def __init__(self, gitlab_id, config_path):
        self.user_token = user_token
        self.gitlab_url = gitlab_url
        self.client = gitlab.Gitlab(url=self.gitlab_url, private_token=self.user_token, timeout=120)
        self.one_user = None
        self.one_group = None
        self.one_project = None


    def get_all_users(self):
        # 获取所有用户
        return self.client.users.list(all=True)

    def user_search_by_username(self, username):
        # 根据username获取user对象
        use_lst = self.client.users.list(username=username)
        if len(use_lst) != 1:
            return None
        self.one_user = use_lst[0]
        return self.one_user

    def get_user_by_id(self, user_id):
        # 根据用户id查找用户详情
        try:
            self.one_user = self.client.users.get(user_id)
        except gitlab.exceptions.GitlabGetError as e:
            return None
        return self.one_user

    def create_user_ssh_key(self,username,key_name,key_content):
        self.user_search_by_username(username=username)
        # 如果存在先删除，在创建
        is_exist = False
        for one_key in self.one_user.keys.list():
            if one_key.attributes['title'] == key_name:
                is_exist = True
                one_key.delete()
        key = self.one_user.keys.create({'title': key_name,
                                    'key': key_content})
        return key


    def del_all_users(self,exclude_lst):
        n = 1
        for one_user in self.get_all_users():
            if one_user.attributes['username'] not in exclude_lst :
                logger.info("DEL [{0}] User {1}".format(n , one_user.attributes['username']))
                one_user.delete()
                n = n + 1
        logger.info("DEL ALL [{0}] User".format(n-1))

    def del_one_user(self, user_id):
        # 删除一个用户
        self.client.users.delete(user_id)

    def create_user(self, **kwargs):
        # 创建用户
        '''
        {
          'email': user_dct['email'],
          'password': new_user_password,
          'username': user_dct['username'],
          'name': user_dct['name']
        }
        '''
        self.client.users.create(kwargs)

    def create_user_project(self, one_dct):
        # 创建用户项目
        '''
        {
            "name": one_pro_dct['name'],
            "description": one_pro_dct['description'],
            "path": one_pro_dct['path']
        }
        '''
        self.one_user.projects.create(one_dct)

    def get_all_projects(self):
        # 获取所有项目
        return self.client.projects.list(all=True)

    def del_all_projects(self):
        # 删除所有项目
        n = 1
        for one_project in self.get_all_projects():
            logger.info("DEL [{0}] Project {1}".format( n ,one_project.attributes['path_with_namespace']))
            one_project.delete()
            n = n + 1
        logger.info("DEL ALL [{0}] Project".format(n-1))

    def create_project(self,**kwargs):
        '''
        {
            "name": one_pro_dct['name'],
            "description": one_pro_dct['description'],
            "path": one_pro_dct['path'],
            "namespace_id": i_group_pid,
            "initialize_with_readme": False,
            "visibility": one_pro_dct['visibility']
        }
        '''
        self.client.projects.create(kwargs)

    def get_project_by_id(self,pro_id):
        ''' 获取单个项目通过ID '''
        self.one_project = self.client.projects.get(pro_id)
        return self.one_project

    def get_project_by_name_with_namespace(self,name_with_namespace):
        ''' 获取单个项目通过name_with_namespace '''
        self.one_project = self.client.projects.get(name_with_namespace)
        return self.one_project


    def get_all_groups(self):
        '''  获取所有组  '''
        return self.client.groups.list(iterator=True, order_by='id')

    def group_search_by_username(self,username):
        # 搜索组username获取group
        group_lst = self.client.groups.list(search=username, obey_rate_limit=False, all=True)
        return group_lst

    def get_group_by_id(self, group_id):
        # 根据用户id查找用户详情
        try:
            self.one_group = self.client.groups.get(group_id)
        except gitlab.exceptions.GitlabGetError as e:
            return None
        return self.one_group

    def del_all_group(self):
        n = 1
        for one_group in self.get_all_groups():
            logger.info("DEL [{0}] Group {1}".format(n ,one_group.attributes['full_path']))
            one_group.delete()
            n = n + 1
        logger.info("DEL ALL [{0}] Group".format(n-1))


    def del_one_group(self,group_id):
        # 删除一个组
        self.get_user_by_id(self, group_id).delete()

    def create_group(self, **kwargs):
        # 创建一个组
        '''
        # 创建顶级组
        one_dct = {
            'name': group_dct['name'],
            'path': group_dct['path'],
            'description': group_dct['description']
        }
        # 创建子组
        one_dct = {
            'name': group_dct['name'],
            'path': group_dct['path'],
            'description': group_dct['description'],
            'parent_id': p_id
        }
        '''
        self.client.groups.create(kwargs)

    ''' 创建单项目的保护分支 参数:保护分支名列表'''
    def create_project_branch_protecte(self, protecte_name_lst):
        for one_protecte_name in protecte_name_lst:
            p_branch = self.one_project.protectedbranches.create({
                'name': one_protecte_name,
                'merge_access_level': gitlab.const.AccessLevel.DEVELOPER,
                'push_access_level': gitlab.const.AccessLevel.MAINTAINER
            })
            logger.info("Create protecte branch: {0}".format(one_protecte_name))


    ''' 删除单项目的所有保护分支 '''
    def del_project_branch_protecte(self):
        for one_protecte_branch in self.one_project.protectedbranches.list() :
            one_protecte_branch.delete()
            logger.info("DEL protecte branch: {0}".format(one_protecte_branch.attributes['name']))


    def get_project_branches(self, name, path_with_namespace):
        # 根据项目名称和组名查找项目
        pros = self.client.projects.list(search=name, obey_rate_limit=False)
        res = []
        if not pros:
            return res
        pro = None
        for _pro in pros:
            if _pro.path_with_namespace == path_with_namespace:
                pro = _pro
        if pro:
            res = pro.branches.list(all=True)
            return res
        return res


    def import_project(self, data):
        # 根据file(xxx.tar.gz)导入项目
        logger.info(data)
        if not data:
            return None
        try:
            res = self.client.projects.import_project(file=open(data['file'], 'rb'), path=data['path'],
                                                      name=data['name'], namespace=data['group'])
        except Exception as e:
            logger.error(e)
            return None
        logger.info(res)
        return res

    def export_project_by_id(self, pk, file_dir, group=None):
        # 根据项目id导出项目(xxx.tar.gz)
        try:
            logger.info(file_dir)
            pro = self.client.projects.get(int(pk))
            logger.info(pro.name)
            export = pro.exports.create()
            export.refresh()
            while export.export_status != 'finished':
                time.sleep(1)
                export.refresh()
                logger.info(export.export_status)
            file_path = os.path.join(file_dir, '%s.tar.gz' % pro.name)
            logger.info(file_path)
            with open(file_path, 'wb') as f:
                export.download( streamed=True, action=f.write )
        except Exception as e:
            logger.error(e)
            return None
        return {'file': file_path, 'name': pro.name, 'path': pro.name, 'group': group}

if __name__ == "__main__":
    print("hello world")

    origin_git_url = 'http://192.168.1.80'
    origin_git_private_token = '5nzY4xxJtC5LBbu9ixyr'
    item_git_url = 'http://192.168.1.81'
    item_git_private_token = 'glpat-PRvG7sCkLgqcQA9ynVxS'
    origin_glm = GitlabManage(origin_git_url, origin_git_private_token)
    item_glm = GitlabManage(item_git_url, item_git_private_token)
    # 代码下载存放基础目录
    CODE_BASE_DIR = 'download'

