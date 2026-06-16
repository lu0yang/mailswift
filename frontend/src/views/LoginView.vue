<template>
  <div class="login-page">
    <div class="login-card">
      <h1 class="login-title">MailSwift</h1>
      <p class="login-subtitle">邮件发送工具</p>

      <n-form ref="formRef" :model="form" :rules="rules" size="large">
        <n-form-item path="email">
          <n-input
            v-model:value="form.email"
            placeholder="邮箱地址"
            :input-props="{ autocomplete: 'email' }"
          />
        </n-form-item>
        <n-form-item path="password">
          <n-input
            v-model:value="form.password"
            type="password"
            placeholder="密码"
            :input-props="{ autocomplete: 'current-password' }"
            @keyup.enter="handleSubmit"
          />
        </n-form-item>
      </n-form>

      <n-button
        type="primary"
        block
        size="large"
        :loading="loading"
        @click="handleSubmit"
      >
        {{ isRegister ? "注册" : "登录" }}
      </n-button>

      <p class="login-toggle">
        {{ isRegister ? "已有账号？" : "没有账号？" }}
        <a href="#" @click.prevent="isRegister = !isRegister; error = ''">
          {{ isRegister ? "去登录" : "去注册" }}
        </a>
      </p>

      <p v-if="error" class="login-error">{{ error }}</p>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from "vue";
import { useRouter } from "vue-router";
import { NForm, NFormItem, NInput, NButton } from "naive-ui";
import { login, register, getToken, setToken } from "@/api";

const router = useRouter();
const loading = ref(false);
const isRegister = ref(false);
const error = ref("");
const form = reactive({ email: "", password: "" });

const rules = {
  email: [{ required: true, message: "请输入邮箱" }],
  password: [{ required: true, message: "请输入密码" }],
};

onMounted(() => {
  // 如果已有 token，直接跳转主页
  if (getToken()) {
    router.replace("/account");
  }
});

async function handleSubmit() {
  error.value = "";
  loading.value = true;
  try {
    const fn = isRegister.value ? register : login;
    const { data } = await fn(form.email, form.password);
    setToken(data.token);
    router.replace("/account");
  } catch (e) {
    error.value = e.message || "操作失败，请重试";
  } finally {
    loading.value = false;
  }
}
</script>

<style scoped>
.login-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #f5f5f7;
}

.login-card {
  width: 400px;
  padding: 48px 40px;
  background: #fff;
  border-radius: 16px;
  box-shadow: 0 2px 20px rgba(0, 0, 0, 0.06);
}

.login-title {
  font-size: 28px;
  font-weight: 700;
  text-align: center;
  color: #1d1d1f;
  margin-bottom: 4px;
}

.login-subtitle {
  text-align: center;
  font-size: 14px;
  color: #86868b;
  margin-bottom: 32px;
}

.login-toggle {
  text-align: center;
  font-size: 13px;
  color: #86868b;
  margin-top: 16px;
}

.login-toggle a {
  color: #0071e3;
  text-decoration: none;
}

.login-error {
  color: #ff3b30;
  font-size: 13px;
  text-align: center;
  margin-top: 12px;
}
</style>
