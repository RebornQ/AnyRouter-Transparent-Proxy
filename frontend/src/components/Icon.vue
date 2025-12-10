<template>
  <svg :class="className" fill="none" viewBox="0 0 24 24" stroke="currentColor">
    <!-- Check Circle (Success) -->
    <path v-if="name === 'check-circle'" stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />

    <!-- X Circle (Error) -->
    <path v-else-if="name === 'x-circle'" stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 14l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2m7-2a9 9 0 11-18 0 9 9 0 0118 0z" />

    <!-- Exclamation Triangle (Warning) -->
    <path v-else-if="name === 'exclamation-triangle'" stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L4.082 16.5c-.77.833.192 2.5 1.732 2.5z" />

    <!-- Information Circle (Info) -->
    <path v-else-if="name === 'information-circle'" stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />

    <!-- X (Close) -->
    <path v-else-if="name === 'x'" stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />

    <!-- Default (Circle) -->
    <circle v-else cx="12" cy="12" r="10" stroke="currentColor" stroke-width="2" />
  </svg>
</template>

<script setup lang="ts">
interface Props {
  name: string
  className?: string
}

withDefaults(defineProps<Props>(), {
  className: 'h-5 w-5'
})
</script>