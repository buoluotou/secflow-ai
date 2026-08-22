import { useEffect } from 'react'
import { Layout, Menu, Dropdown, Avatar, Typography, Space } from 'antd'
import {
  DashboardOutlined,
  ProjectOutlined,
  HddOutlined,
  ThunderboltOutlined,
  BugOutlined,
  SafetyCertificateOutlined,
  AlertOutlined,
  ScanOutlined,
  RobotOutlined,
  FileTextOutlined,
  AuditOutlined,
  SettingOutlined,
  LogoutOutlined,
  UserOutlined,
} from '@ant-design/icons'
import { Outlet, useLocation, useNavigate } from 'react-router-dom'
import { useAuthStore } from '../store/auth'
import { authApi } from '../services/api'

const { Sider, Header, Content } = Layout

const MENU = [
  { key: '/dashboard', icon: <DashboardOutlined />, label: 'Dashboard 总览' },
  { key: '/projects', icon: <ProjectOutlined />, label: 'Projects 项目' },
  { key: '/assets', icon: <HddOutlined />, label: 'Assets 资产' },
  { key: '/events', icon: <ThunderboltOutlined />, label: 'Events 安全事件' },
  { key: '/findings', icon: <BugOutlined />, label: 'Findings 漏洞' },
  { key: '/iocs', icon: <SafetyCertificateOutlined />, label: 'IOCs 威胁情报' },
  { key: '/incidents', icon: <AlertOutlined />, label: 'Incidents 事件' },
  { key: '/scans', icon: <ScanOutlined />, label: 'Scans 扫描任务' },
  { key: '/analysis', icon: <RobotOutlined />, label: 'AI Analysis' },
  { key: '/reports', icon: <FileTextOutlined />, label: 'Reports 报告' },
  { key: '/audit', icon: <AuditOutlined />, label: 'Audit 审计' },
  { key: '/settings', icon: <SettingOutlined />, label: 'Settings 设置' },
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
      <Sider theme="dark" width={220}>
        <div style={{ padding: '16px', color: '#fff', fontWeight: 700, fontSize: 16 }}>
          🛡️ SecFlow AI
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
        <Header style={{ background: '#fff', padding: '0 24px', display: 'flex', justifyContent: 'flex-end', alignItems: 'center' }}>
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
              <Typography.Text type="secondary" style={{ fontSize: 12 }}>
                {user?.role}
              </Typography.Text>
            </Space>
          </Dropdown>
        </Header>
        <Content style={{ margin: 16 }}>
          <Outlet />
        </Content>
      </Layout>
    </Layout>
  )
}
