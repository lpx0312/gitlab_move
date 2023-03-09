

# 项目背景

```
    因需要迁移低版本gitlab代码仓数据 -> 高版本gitlab代码仓中,
    使用导出工具,兼容性不佳,所以只能手写脚本
```

# 项目使用要求

```
1. 需要运行脚本的机器，必须可以连接两边的gitlab仓库，网络权限OK
2. 必须获取两边gitlab的token
3. 运行机器必须安装docker,要不然还需安装python很麻烦
```

# 使用方法

## 一、备份源gitlab和目标gitlab的数据，以防万一

- 虚机请直接执行命令
```bash
echo "停止puma和sidekiq"
docker exec -t gitlab gitlab-ctl stop puma
docker exec -t gitlab gitlab-ctl stop sidekiq
echo "备份配置文件"
docker exec -t gitlab gitlab-ctl backup-etc
echo "备份应用(全备份)"
docker exec -t gitlab gitlab-backup create
echo "备份完成开启服务"

docker exec -t gitlab gitlab-ctl start puma
docker exec -t gitlab gitlab-ctl start sidekiq
```


## 二、构建脚本执行的容器
```bash
    docker build -t gitlab-python:3.13.0 .
```

## 三、更改配置文件
- 也可以后续进入容器，进行更改。容器中有vim命令
```ini
# 源Gitlab信息
[origin-gialab]
url = http://192.168.1.80
private_token = 5nzY4xxJtC5LBbu9ixyr

# 目标Gitlab信息
[item-gialab]
url = http://192.168.1.81
private_token = glpat-PRvG7sCkLgqcQA9ynVxS

# 迁移策略
[move-setting]
##### 日志路径 #####
log_path = gitlab_move.log

#####  重置目标Gitlab 慎用  #####
# 是否迁移前删除目标Gitlab所有项目,包含用户项目和组项目
del_all_project = false
# 是否迁移前删除所有用户除了root
del_all_user = false
# 是否迁移前删除所有组
del_all_group = false

# 是否迁移源Gitlab用户到目标Gitlab中
# 如果目标Gitlab中存在用户,就跳过创建用户
# 如果move_user=true 则必须填写新建用户的密码，而且是统一的。
# 不管源Gitlab的用户时啥类型的，只能创建一般的本地用户，不能创建ldap账户。
gitlab_move_users = false
new_user_password = 12345678

# 是否在目标Gitlab中创建组，如果目标Gitlab中没有组，迁移仓库时会报错, 所以必须创建
# 如果目标Gitlab中存在源Gitlab的组，就跳过
gitlab_move_groups = true

# 是否创建和更新目标Gitlab的用户项目
# no_user = true 代表 不创建用户的空项目 也不更新用户的项目
# no_user = false 代表 既创建用户空项目，也要更新用户项目
no_user = true

####### 新建空项目 #######
# 新建目标Gitlab空项目
# 如果目标Gitlab空项目已存在，则不创建
gitlab_move_projects = true

####### 更新目标Gitlab项目数据 #######
gitlab_all_repo_move = true
# 下载代码的存放目录
CODE_BASE_DIR = download
# 下载代码仓和推送代码仓的方式

# 如果是ssh, 则必须填写 origin_ssh_port 和 item_ssh_port
# 如果是http，则origin_ssh_port 和 item_ssh_port 不会生效
download_code_type = ssh
origin_ssh_port = 2022
item_ssh_port = 2022
```


## 三、启动执行脚本的容器
```bash
    docker run -itd --name=gitlab-python -v $(pwd):/root/ gitlab-python:3.13.0
```

## 四、并且执行脚本
```bash
    docker exec -t gitlab-python  python gitlab_move.py
```


