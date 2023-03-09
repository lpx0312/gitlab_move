#!/usr/bin/env python
# -*- coding: UTF-8 -*-
import shutil
import os
# from GitlabManage import GitlabManage
from GitlabManage import *
import subprocess
import time
import sys

''' 根据源gitlab组id获取目标gitlab组id'''
def getItemPid(o_glm,origin_p_id,i_glm):
    # print("============ 组内: =============")
    # print("源组ID:{0}".format(origin_p_id))
    for one_group in o_glm.get_all_groups() :
        if one_group.attributes['id'] == origin_p_id:
            p_group = one_group
    p_full_path = p_group.attributes['full_path']
    # print("源组full_path:{0}".format(p_full_path))
    p_name = p_group.attributes['name']
    # print("源组name:{0}".format(p_name))
    i_groups = i_glm.group_search_by_username(p_name)
    # print("i_groups",i_groups)
    for i_one_group in i_groups:
        # print("i_one_group.attributes['full_path']",i_one_group.attributes['full_path'])
        if i_one_group.attributes['full_path'] == p_full_path:
            i_one_group_id = i_one_group.attributes['id']
            # print("目标组ID:{0}".format(i_one_group_id))
            # print("目标组name:{0}".format(i_one_group.attributes['name']))
            # print("目标组full_path:{0}".format(i_one_group.attributes['full_path']))
            return i_one_group_id


''' 迁移用户 
    如果目标Gitlab中存在用户,就跳过创建用户
'''
def gitlab_move_users(origin_glm,item_glm,new_user_password):
    item_username_lst = [ item_one_user.attributes['username'] for item_one_user in item_glm.get_all_users()]
    all_user_obj = origin_glm.get_all_users()
    n = 1
    for one_user in all_user_obj :
        user_dct = one_user.attributes
        if user_dct['username'] in item_username_lst :
            logger.warning("User = {0} is exist in Item Gitlab,skip".format(user_dct['username']))
            continue
        dct = {
            'email': user_dct['email'],
            'password': new_user_password,
            'username': user_dct['username'],
            'name': user_dct['name'],
            'skip_confirmation': True
        }
        if user_dct['username'] != 'root' :
            item_glm.create_user(**dct)
            logger.info("Create User [{0}] : {1}".format(n, user_dct['username']))
            n = n + 1
    logger.info("Create ALL [{0}] User".format(n-1))

''' 迁移组: 包含顶级组和子组
    如果目标Gitlab中存在该组，就跳过创建组 
'''
def gitlab_move_groups(origin_glm,item_glm):
    item_group_full_path_lst = [ item_one_group.attributes['full_path'] for item_one_group in item_glm.get_all_groups()]
    all_group_obj = origin_glm.get_all_groups()
    n = 1
    for one_group in all_group_obj :
        group_dct = one_group.attributes
        if group_dct['full_path'] in item_group_full_path_lst:
            logger.warning("Group = {0} is exist in Item Gitlab,skip".format(group_dct['full_path']))
            continue
        one_dct = {
            'name': group_dct['name'],
            'path': group_dct['path'],
            'description': group_dct['description']
        }
        if group_dct['parent_id'] :
            i_pid = getItemPid(origin_glm, group_dct['parent_id'], item_glm)
            one_dct['parent_id'] = i_pid
        logger.info("Create Group [{0}] : {1}".format(n ,group_dct['full_path']))
        item_glm.create_group(**one_dct)
        n = n + 1
    logger.info("Create ALL [{0}] Group".format(n-1))


''' 新建目标Gitlab所有项目空仓库 '''
def gitlab_move_projects(origin_glm, item_glm, no_user = False):
    item_pro_path_with_namespace_lst = [ item_one_pro.attributes['path_with_namespace'] for item_one_pro in item_glm.get_all_projects()]
    one_project_obj = origin_glm.get_all_projects()
    n = 1
    for one_peoject in one_project_obj :
        one_pro_dct = one_peoject.attributes
        if one_pro_dct['path_with_namespace'] in item_pro_path_with_namespace_lst:
            logger.warning("Project = {0} is exist in Item Gitlab,skip".format(one_pro_dct['path_with_namespace']))
            continue
        pro_type = one_pro_dct['namespace']['kind']
        one_dct = {
            "name": one_pro_dct['name'],
            "description": one_pro_dct['description'],
            "path": one_pro_dct['path']
        }
        if pro_type == 'user' and no_user:
            logger.warning("no_user = True Skip User Project :{0}".format(one_pro_dct['path_with_namespace']))
            continue
        elif pro_type == 'user' and not no_user :
            ''' 创建用户 项目 '''
            user_name = one_pro_dct['namespace']['full_path']
            item_glm.user_search_by_username(user_name)
            logger.info("Create User Project [{0}] : user={1}, project: {2}".format(n ,user_name, one_pro_dct['path_with_namespace']))
            item_glm.create_user_project(one_dct)
            n = n + 1
        elif pro_type == 'group' :
            ''' 创建组 项目'''
            logger.info("Create Project [{0}] : {1}".format(n ,one_pro_dct['path_with_namespace']))
            i_pid = getItemPid(origin_glm, one_pro_dct['namespace']['id'], item_glm)
            one_dct.update({'namespace_id':i_pid,'initialize_with_readme':False,'visibility':one_pro_dct['visibility']})
            item_glm.create_project(**one_dct)
            n = n + 1
    logger.info("Create ALL [{0}] EMPTY Project".format(n-1))



''' 创建密钥对 '''
def create_hosted_ssh_key():
    if os.path.exists('{0}/.ssh/id_rsa.pub'.format(os.environ['HOME'])):
        logger.info("ssh key is exist,skip")
        return 1
    ret = subprocess.run("ssh-keygen -t rsa -f ~/.ssh/id_rsa -N ''", shell=True, stdout=subprocess.PIPE,
                         stderr=subprocess.PIPE, encoding="utf-8")
    if ret.returncode != 0 :
        logger.error("Create ssh key Failed")
        logger.error("{0}".format(ret.stderr))
        return 0
    logger.info("Create ssh key Success")
    return 1

''' 写入known_hosts,避免首次交互输入yes '''
def created_ip_known_hosts(ip,port):
    ret = subprocess.run("ssh-keyscan -p {0} {1} >> ~/.ssh/known_hosts".format(port ,ip), shell=True, stdout=subprocess.PIPE,
                         stderr=subprocess.PIPE, encoding="utf-8")
    if ret.returncode != 0:
        logger.error("Write {0}:{1} into known_hosts Failed".format(ip, port))
        logger.error("{0}".format(ret.stderr))
        return 0
    logger.info("Write {0}:{1} into known_hosts Success".format(ip, port))
    return 1

''' 迁移仓库数据 '''
def gitlab_all_repo_move(origin_glm,item_glm,CODE_BASE_DIR, no_user = False, url_type = 'http',origin_ssh_port = '22',item_ssh_port = '22'):
    if url_type == "ssh" :
        create_hosted_ssh_key()
        created_ip_known_hosts(origin_glm.gitlab_url.replace('http://',''), origin_ssh_port)
        created_ip_known_hosts(item_glm.gitlab_url.replace('http://',''), item_ssh_port)
        origin_glm.create_user_ssh_key('root', 'gitlab_move_key', open('{0}/.ssh/id_rsa.pub'.format(os.environ['HOME'])).read())
        item_glm.create_user_ssh_key('root', 'gitlab_move_key', open('{0}/.ssh/id_rsa.pub'.format(os.environ['HOME'])).read())
    n = 1
    CURRENT_DIR = os.getcwd()
    for origin_one_project in origin_glm.get_all_projects():
        logger.info("===================[ {0} ]======================".format(n))
        logger.info("ORIGIN_URL = {0}".format(origin_one_project.attributes['http_url_to_repo']))
        project_name_path = origin_one_project.attributes['path_with_namespace']
        if no_user and origin_one_project.attributes['namespace']['kind'] == 'user'  :
            logger.warning("no_user = True Skip User Project Update :{0}".format(project_name_path))
            continue
        item_one_project = item_glm.get_project_by_name_with_namespace(project_name_path)
        # 项目组路径: full_path
        project_group_path = origin_one_project.attributes['namespace']['full_path']
        # 代码存放目录
        group_dir = "{0}/{1}/{2}".format(CURRENT_DIR ,CODE_BASE_DIR, project_group_path)
        # 源gitlab项目下载地址
        origin_code_url = "http://oauth2:{0}@{1}/{2}.git".format(
                        origin_glm.user_token,
                        origin_glm.gitlab_url.replace("http://", ''),
                        project_name_path )
        # 目标gitlab项目下载地址
        item_code_url = "http://oauth2:{0}@{1}/{2}.git".format(
                        item_glm.user_token,
                        item_glm.gitlab_url.replace("http://", ''),
                        project_name_path)
        if url_type == "ssh" :
            origin_code_url = origin_one_project.attributes['ssh_url_to_repo']
            item_code_url = origin_code_url.replace(origin_glm.gitlab_url.replace("http://", ''),item_glm.gitlab_url.replace("http://", ''))
        # print(origin_code_url)
        # print(item_code_url)
        # 代码下载后的目录
        gitcode_dir_name = origin_code_url.split("/")[-1].replace(".git","")
        # 新建GROUP目录
        if os.path.exists(group_dir):
            shutil.rmtree(group_dir)
        os.makedirs(group_dir)
        # 切换到 下载项目目录
        os.chdir(group_dir)
        logger.info("Starting Move Project: {0}".format(project_name_path))
        ret = subprocess.run('git clone --bare {0}'.format(origin_code_url), shell=True, stdout=subprocess.PIPE,stderr=subprocess.PIPE,encoding="utf-8")
        if ret.returncode != 0 :
            logger.error("Project Clone Failed")
            logger.error("{0}".format(ret.stderr))
            break
        logger.info("Success Project Clone")
        if ret.stderr.find("empty repository") != -1:
            logger.warning("Project is empty,not push")
            continue

        # 进入项目下载后的目录
        os.chdir("{0}.git".format(gitcode_dir_name))
        # 更改远程仓库地址为目标仓库地址
        ret = subprocess.run('git remote set-url origin {0}'.format(item_code_url), shell=True, stdout=subprocess.PIPE,stderr=subprocess.PIPE,encoding="utf-8")
        if ret.returncode != 0 :
            logger.error("Project set-url Failed ")
            logger.error("{0}".format(ret.stderr))
            break
        logger.info("Success Project set-url")

        # 删除目标Gilab的项目保护分支
        one_item_project_protecte_name_lst = [ one_protecte_branch.attributes['name']
                                               for one_protecte_branch in
                                               item_one_project.protectedbranches.list()]
        # 删除目标Gitlab中的保护分支
        if one_item_project_protecte_name_lst :
            logger.info("protecte branch: {0}".format(one_item_project_protecte_name_lst))
            item_glm.del_project_branch_protecte()

        # 推送源项目到目标Gitlab
        try:
            ret = subprocess.run('git push --mirror', shell=True, stdout=subprocess.PIPE,stderr=subprocess.PIPE,encoding="utf-8")
        except Exception as e:
            item_glm.create_project_branch_protecte(one_item_project_protecte_name_lst)
            logger.error(e)
            sys.exit(1)

        if ret.returncode != 0:
            logger.error("Project Push Failed")
            logger.error("{0}".format(ret.stderr))
            item_glm.create_project_branch_protecte(one_item_project_protecte_name_lst)
            break
        # 恢复保护分支
        item_glm.create_project_branch_protecte(one_item_project_protecte_name_lst)
        logger.info("Success Project Push ")
        logger.info("ITEM_URL = {0}".format(item_one_project.attributes['http_url_to_repo']))
        n = n + 1
    logger.info("Update ALL [{0}] Project".format(n-1))

def str_convert_bool(str):
    if str == "true" :
        return True
    elif str == "false" :
        return False
    else:
        logger.error("config str convert bool failed")
        sys.exit(1)




if __name__ == "__main__" :
    origin_git_url = config.get('origin-gialab', 'url')
    origin_git_private_token = config.get('origin-gialab', 'private_token')
    item_git_url = config.get('item-gialab', 'url')
    item_git_private_token = config.get('item-gialab', 'private_token')

    origin_glm = GitlabManage(origin_git_url, origin_git_private_token)
    item_glm = GitlabManage(item_git_url, item_git_private_token)
    # 代码下载存放基础目录
    CODE_BASE_DIR = config.get('move-setting', 'CODE_BASE_DIR')


    ########### 重置目标Gitlab 慎用 #########
    if str_convert_bool(config.get('move-setting', 'del_all_project')):
        print_title("删除所有项目")
        item_glm.del_all_projects()

    if str_convert_bool(config.get('move-setting', 'del_all_user')):
        print_title("删除所有用户,除了root")
        item_glm.del_all_users(exclude_lst=['root'])

    if str_convert_bool(config.get('move-setting', 'del_all_group')):
        print_title("删除所有组")
        item_glm.del_all_group()
        # 等待两分钟，待重置完成。
        time.sleep(120)

    # 迁移用户
    if str_convert_bool(config.get('move-setting', 'gitlab_move_users')):
        new_user_password = config.get('move-setting', 'new_user_password')
        print_title("+".join(["迁移用户:","如果目标Gitlab中存在用户,就跳过创建用户",
                              "默认密码:{0}".format(new_user_password)
                              ]))
        gitlab_move_users(origin_glm = origin_glm, item_glm = item_glm, new_user_password = new_user_password)

    # 迁移组
    if str_convert_bool(config.get('move-setting', 'gitlab_move_groups')):
        print_title("+".join(["迁移组: ","包含顶级组和子组",
                              "如果目标Gitlab中存在该组,就跳过创建组"]))
        gitlab_move_groups(origin_glm = origin_glm, item_glm = item_glm)

    # 是否创建和更新目标Gitlab的用户项目
    no_user = str_convert_bool(config.get('move-setting', 'no_user'))

    # 新建空项目
    if str_convert_bool(config.get('move-setting', 'gitlab_move_projects')):
        title = "+".join(["新建目标Gitlab所有项目空仓库","no_user = {0}".format(no_user)])
        print_title(title)
        gitlab_move_projects(origin_glm = origin_glm, item_glm = item_glm, no_user = no_user)


    ''' 迁移项目数据 
        url_type 默认是http方式,如果是默认url_type,origin_ssh_port和item_ssh_port可以不用填写
        不管目标Gitlab的仓库是否存在，都强制更新目标代码仓库内容
    '''
    if str_convert_bool(config.get('move-setting', 'gitlab_all_repo_move')):
        url_type = config.get('move-setting', 'download_code_type')
        origin_ssh_port = config.get('move-setting', 'origin_ssh_port')
        item_ssh_port = config.get('move-setting', 'item_ssh_port')
        if url_type == "ssh" :
            title = "+".join(["迁移仓库数据","url_type = {0}".format(url_type),
                              "origin_ssh_port = {0}".format(origin_ssh_port),
                              "item_ssh_port = {0}".format(item_ssh_port),
                              "no_user = {0}".format(no_user)])
        else:
            title = "+".join(["迁移仓库数据","url_type = {0}".format("http"),
                              "no_user = {0}".format(no_user)])
        print_title(title)
        gitlab_all_repo_move(origin_glm = origin_glm , item_glm = item_glm,
                             CODE_BASE_DIR = CODE_BASE_DIR, no_user = True ,
                             url_type=url_type, origin_ssh_port='2022', item_ssh_port='2022')
