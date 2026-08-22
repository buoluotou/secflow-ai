import { useEffect } from 'react'
import { Layout, Menu, Dropdown, Avatar, Typography, Space } from 'antd'
import {
  DashboardOutlined,
  AlertOutlined,
  BugOutlined,
  ScanOutlined,
  FileTextOutlined,
  SettingOutlined,
  LogoutOutlined,
  UserOutlined,
} from '@ant-design/icons'
import { Outlet, useLocation, useNavigate } from 'react-router-dom'
import { useAuthStore } from '../store/auth'
import { authApi } from '../services/api'

const { Sider, Header, Content } = Layout

// 精简菜单：只保留核心工作流
const MENU = [
  { key: '/dashboard', icon: <DashboardOutlined />, label: '总览' },
  { key: '/incidents', icon: <AlertOutlined />, label: '安全事件' },
  { key: '/findings', icon: <BugOutlined />, label: '漏洞' },
  { key: '/scans', icon: <ScanOutlined />, label: '扫描' },
  { key: '/reports', icon: <FileTextOutlined />, label: '报告' },
  { key: '/settings', icon: <SettingOutlined />, label: '设置' },
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
      <Sider theme="dark" width={170}>
        <div style={{ padding: '14px 16px', color: '#fff', fontWeight: 700, fontSize: 15 }}>
          🛡️ SecFlow
        </div>
        <Menu
          theme="dark"
          mode="inline"
          selectedKeys={[selectedKey]}
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
