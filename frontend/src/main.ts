import { app, BrowserWindow, Menu, ipcMain } from 'electron'
import { join } from 'path'
import { electronApp, optimizer, is } from '@electron-toolkit/utils'

function createWindow(): void {
  const mainWindow = new BrowserWindow({
    width: 1200,
    height: 800,
    minWidth: 1000,
    minHeight: 600,
    show: false,
    autoHideMenuBar: true,
    webPreferences: {
      preload: join(__dirname, '../preload/index.js'),
      sandbox: false,
      nodeIntegration: true,
      contextIsolation: false
    },
    titleBarStyle: 'default',
    title: '웹 접근성 검사 도구'
  })

  mainWindow.on('ready-to-show', () => {
    mainWindow.show()
    
    if (is.dev) {
      mainWindow.webContents.openDevTools()
    }
  })

  mainWindow.webContents.setWindowOpenHandler((details) => {
    require('electron').shell.openExternal(details.url)
    return { action: 'deny' }
  })

  if (is.dev && process.env['ELECTRON_RENDERER_URL']) {
    mainWindow.loadURL(process.env['ELECTRON_RENDERER_URL'])
  } else {
    mainWindow.loadFile(join(__dirname, '../renderer/index.html'))
  }
}

app.whenReady().then(() => {
  electronApp.setAppUserModelId('com.accchecker.app')

  app.on('browser-window-created', (_, window) => {
    optimizer.watchWindowShortcuts(window)
  })

  // IPC 이벤트 핸들러 등록
  ipcMain.handle('check-accessibility', async (event, url: string, options: any) => {
    // 백엔드 API 호출 로직
    const axios = require('axios')
    try {
      const response = await axios.post('http://127.0.0.1:8000/check', {
        url: url,
        options: options
      })
      return response.data
    } catch (error) {
      throw new Error(`접근성 검사 실패: ${error.message}`)
    }
  })

  ipcMain.handle('get-app-version', () => {
    return app.getVersion()
  })

  createWindow()

  app.on('activate', function () {
    if (BrowserWindow.getAllWindows().length === 0) createWindow()
  })
})

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') app.quit()
})

// 메뉴 설정
const template = [
  {
    label: '파일',
    submenu: [
      {
        label: '새 검사',
        accelerator: 'CmdOrCtrl+N',
        click: () => {
          // 새 검사 시작
        }
      },
      {
        label: '보고서 내보내기',
        accelerator: 'CmdOrCtrl+E',
        click: () => {
          // 보고서 내보내기
        }
      },
      { type: 'separator' },
      {
        label: '종료',
        accelerator: process.platform === 'darwin' ? 'Cmd+Q' : 'Ctrl+Q',
        click: () => {
          app.quit()
        }
      }
    ]
  },
  {
    label: '도구',
    submenu: [
      {
        label: '설정',
        accelerator: 'CmdOrCtrl+,',
        click: () => {
          // 설정 창 열기
        }
      },
      { type: 'separator' },
      {
        label: '개발자 도구',
        accelerator: 'F12',
        click: () => {
          BrowserWindow.getFocusedWindow()?.webContents.toggleDevTools()
        }
      }
    ]
  },
  {
    label: '도움말',
    submenu: [
      {
        label: '사용법',
        click: () => {
          // 도움말 창 열기
        }
      },
      {
        label: '정보',
        click: () => {
          // 앱 정보 창 열기
        }
      }
    ]
  }
]

Menu.setApplicationMenu(Menu.buildFromTemplate(template))