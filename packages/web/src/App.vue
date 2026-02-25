<script setup lang="ts">
import { useRouter } from 'vue-router'

const router = useRouter()
</script>

<template>
  <el-container class="app-layout">
    <el-header class="app-header">
      <div class="header-left" @click="router.push('/')">
        <span class="logo">Theia</span>
        <span class="tagline">论文视频生成</span>
      </div>
      <el-menu
        mode="horizontal"
        :default-active="$route.path"
        :ellipsis="false"
        router
        class="header-menu"
      >
        <el-menu-item index="/">上传论文</el-menu-item>
        <el-menu-item index="/tasks">任务列表</el-menu-item>
        <el-menu-item index="/settings">设置</el-menu-item>
      </el-menu>
    </el-header>
    <el-main class="app-main">
      <router-view />
    </el-main>
  </el-container>
</template>

<style>
:root {
  --brand: #6366f1;
  --brand-light: #818cf8;
}

* { margin: 0; padding: 0; box-sizing: border-box; }

body {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  background: #f5f5f7;
  color: #1d1d1f;
}

.app-layout {
  min-height: 100vh;
}

.app-header {
  display: flex;
  align-items: center;
  background: #fff;
  border-bottom: 1px solid #e5e5e7;
  padding: 0 24px;
  height: 60px !important;
}

.header-left {
  display: flex;
  align-items: baseline;
  gap: 10px;
  cursor: pointer;
  margin-right: 40px;
  flex-shrink: 0;
}

.logo {
  font-size: 22px;
  font-weight: 700;
  background: linear-gradient(135deg, var(--brand), #a855f7);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
}

.tagline {
  font-size: 13px;
  color: #86868b;
}

.header-menu {
  border-bottom: none !important;
  flex: 1;
}

.header-menu .el-menu-item {
  font-size: 14px;
}

.app-main {
  max-width: 1100px;
  margin: 0 auto;
  padding: 32px 24px;
  width: 100%;
}
</style>
