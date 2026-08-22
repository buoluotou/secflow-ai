import { useEffect } from 'react'
import { Layout, Menu, Dropdown, Avatar, Typography, Space } from 'antd'
import {
  DashboardOutlined,
  AlertOutlined,
  BugOutlined,
  FileTextOutlined,
  SearchOutlined,
  ToolOutlined,
  LogoutOutlined,
  UserOutlined,
} from '@ant-design/icons'
import { Outlet, useLocation, useNavigate } from 'react-router-dom'
import { useAuthStore } from '../store/auth'
import { authApi } from '../services/api'

const { Sider, Header, Content } = Layout

// 安服大模块导航：总览 / 事件响应 / 漏洞管理 / 安全报告 / 日志审查 / 系统维护
const MENU = [
  { key: '/dashboard', icon: <DashboardOutlined />, label: '总览' },
  { key: '/incidents', icon: <AlertOutlined />, label: '事件响应' },
  { key: '/findings', icon: <BugOutlined />, label: '漏洞管理' },
  { key: '/reports', icon: <FileTextOutlined />, label: '安全报告' },
  { key: '/audit', icon: <SearchOutlined />, label: '日志审查' },
  { key: '/maintenance', icon: <ToolOutlined />, label: '系统维护' },
]

export default function MainLayout() {
  const navigate = useNavigate()
  const location = useLocation()
  const { token, user, setUser, logout } = useAuthStore()

  useEffect(() => {
    if (token && !user) {
      authApi.me().then(setUser).catch(() => logout())
    }
  }, [token, user, setUser, logout])

  const selectedKey =
    MENU.map((m) => m.key)
      .filter((k) => location.pathname.startsWith(k))
      .sort((a, b) => b.length - a.length)[0] ?? '/dashboard'

  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Sider theme="dark" width={180}>
        <div style={{ padding: '14px 16px', color: '#fff', fontWeight: 700, fontSize: 15 }}>
          🛡️ SecFlow
          <div style={{ fontSize: 11, fontWeight: 400, opacity: 0.7, marginTop: 2 }}>安全服务</div>
        </div>
        <Menu
          theme="dark" mode="inline" selectedKeys={[selectedKey]}
          items={MENU}
          onClick={({ key }) => navigate(key)}
        />
      </Sider>
      <Layout>
        <Header style={{ background: '#fff', padding: '0 20px', display: 'flex', justifyContent: 'flex-end', alignItems: 'center' }}>
          <Dropdown
            menu={{
              items: [
                { key: 'logout', icon: <LogoutOutlined />, label: '退出登录', onClick: () => { logout(); navigate('/login') } },
              ],
            }}
          >
            <Space style={{ cursor: 'pointer' }}>
              <Avatar size="small" icon={<UserOutlined />} />
              <Typography.Text>{user?.full_name || user?.username || '未登录'}</Typography.Text>
            </Space>
          </Dropdown>
        </Header>
        <Content style={{ margin: 14 }}>
          <Outlet />
        </Content>
      </Layout>
    </Layout>
  )
}
