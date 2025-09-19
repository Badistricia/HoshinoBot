#!/bin/bash

# --- 配置区 START ---
APP_NAME="My Python Application"        # 应用名称，用于友好的提示信息
PYTHON_SCRIPT="run.py"                   # 要运行的 Python 脚本
PORT_TO_CHECK=8081                       # 需要检查和管理的端口
# --- 配置区 END ---

LOG_FILE="app.log"                       # 日志文件路径

# --- 函数定义 START ---

# 检查端口是否被占用
is_port_in_use() {
    sudo netstat -tuln | grep ":$1\s" | grep "LISTEN" > /dev/null
    return $?
}

# 杀死占用指定端口的进程
kill_process_on_port() {
    echo "端口 $1 正在被占用，尝试查找并杀死相关进程..."
    # 查找占用端口的进程ID
    PID=$(sudo lsof -t -i :$1)

    if [ -z "$PID" ]; then
        echo "未找到占用端口 $1 的进程ID。可能需要手动检查或权限不足。"
        return 1
    else
        echo "找到占用端口 $1 的进程ID: $PID"
        sudo kill -9 $PID
        if [ $? -eq 0 ]; then
            echo "进程 $PID 已强制终止。"
            sleep 1 # 等待系统释放端口
            return 0
        else
            echo "无法终止进程 $PID。可能需要root权限或手动干预。"
            return 1
        fi
    fi
}

# 启动应用
start_app() {
    if [ "$1" == "background" ]; then
        echo "----------------------------------------------------"
        echo "在后台启动 $APP_NAME... 日志输出到 $LOG_FILE"
        echo "您可以运行 'tail -f $LOG_FILE' 查看日志。"
        echo "----------------------------------------------------"
        nohup python $PYTHON_SCRIPT > $LOG_FILE 2>&1 &
        if [ $? -eq 0 ]; then
            echo "$APP_NAME 已在后台成功启动。PID: $!"
        else
            echo "后台启动 $APP_NAME 失败。"
        fi
    else
        echo "----------------------------------------------------"
        echo "在前台启动 $APP_NAME... 日志将直接输出到当前终端"
        echo "按 Ctrl+C 终止应用。"
        echo "----------------------------------------------------"
        python $PYTHON_SCRIPT
        if [ $? -eq 0 ]; then
            echo "$APP_NAME 已停止。"
        else
            echo "前台启动 $APP_NAME 失败或异常退出。"
        fi
    fi
}

# --- 函数定义 END ---


echo "--- $APP_NAME 启动脚本 ---"

# 检查端口是否被占用
if is_port_in_use $PORT_TO_CHECK; then
    echo "警告：端口 $PORT_TO_CHECK 正在被占用。"
    read -p "是否尝试关闭占用端口的应用程序？(y/n): " confirm_kill
    if [[ "$confirm_kill" =~ ^[Yy]$ ]]; then
        if kill_process_on_port $PORT_TO_CHECK; then
            echo "端口 $PORT_TO_CHECK 已成功释放。"
        else
            echo "无法释放端口 $PORT_TO_CHECK。请手动检查并解决问题后重试。"
            exit 1 # 退出脚本
        fi
    else
        echo "用户选择不关闭。脚本退出。"
        exit 0 # 退出脚本
    fi
else
    echo "端口 $PORT_TO_CHECK 未被占用，可以直接启动 $APP_NAME。"
fi

# 询问用户启动方式
echo ""
echo "请选择 $APP_NAME 的运行方式："
echo "1) 后台运行 (日志输出到 $LOG_FILE)"
echo "2) 前台运行 (日志输出到当前终端)"
read -p "请输入你的选择 (1/2): " run_choice

case $run_choice in
    1)
        start_app "background"
        ;;
    2)
        start_app "foreground"
        ;;
    *)
        echo "无效的选择。脚本退出。"
        exit 1
        ;;
esac

echo "脚本执行完毕。"

