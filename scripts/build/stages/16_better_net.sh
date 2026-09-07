#!/bin/bash
# ============================================================
# 16 · 启用网络功能增强优化配置（仅 better_net=true 时调用）
# ipset/iptables 高级网络功能 + IP6_NF_NAT + config.patch 隐藏（规避 vintf 检测）
# ============================================================
source "$(dirname "$0")/../lib.sh"

cd "$KS"
#部分机型的 better_net 变体启用 BPF 流解析器（BETTERNET_BPF=1，由 workflow env 控制）
if [[ "$BETTERNET_BPF" == "1" ]]; then
  #启用  BPF 流解析器,实现高性能网络流量处理,增强网络监控和分析能力
  cfg "CONFIG_BPF_STREAM_PARSER=y"
fi
#开启增强 Netfilter 防火墙扩展模块,支持基于地址类型的匹配规则,启用 IP 集合支持,提高防火墙规则灵活性,支持更复杂的流量过滤策略
cfg "CONFIG_NETFILTER_XT_MATCH_ADDRTYPE=y"
cfg "CONFIG_NETFILTER_XT_SET=y"
#启用 IP 集框架及其多种数据结构实现,提供高效的大规模 IP 地址管理,提高防火墙规则处理效率,减少内存占用
cfg "CONFIG_IP_SET=y"
cfg "CONFIG_IP_SET_MAX=65534"
cfg "CONFIG_IP_SET_BITMAP_IP=y"
cfg "CONFIG_IP_SET_BITMAP_IPMAC=y"
cfg "CONFIG_IP_SET_BITMAP_PORT=y"
cfg "CONFIG_IP_SET_HASH_IP=y"
cfg "CONFIG_IP_SET_HASH_IPMARK=y"
cfg "CONFIG_IP_SET_HASH_IPPORT=y"
cfg "CONFIG_IP_SET_HASH_IPPORTIP=y"
cfg "CONFIG_IP_SET_HASH_IPPORTNET=y"
cfg "CONFIG_IP_SET_HASH_IPMAC=y"
cfg "CONFIG_IP_SET_HASH_MAC=y"
cfg "CONFIG_IP_SET_HASH_NETPORTNET=y"
cfg "CONFIG_IP_SET_HASH_NET=y"
cfg "CONFIG_IP_SET_HASH_NETNET=y"
cfg "CONFIG_IP_SET_HASH_NETPORT=y"
cfg "CONFIG_IP_SET_HASH_NETIFACE=y"
cfg "CONFIG_IP_SET_LIST_SET=y"
#启用 IPv6 网络地址转换
cfg "CONFIG_IP6_NF_NAT=y"
cfg "CONFIG_IP6_NF_TARGET_MASQUERADE=y"
#由于部分机型的vintf兼容性检测规则，在开启CONFIG_IP6_NF_NAT后开机会出现"您的设备内部出现了问题。请联系您的设备制造商了解详情。"的提示，故添加一个配置修复补丁，在编译内核时隐藏CONFIG_IP6_NF_NAT=y但不影响对应功能编译
cd "$COMMON"
apply_self_patch "$PLATFORM_DIR/other_patch/config.patch" "-p1" "-F 3" || true
