<template>
  <footer class="site-footer">
    <div class="footer-col footer-col-about">
      <div class="footer-title">Этот сайт реализовала команда «Абстрактный IT»</div>
    </div>
    <div class="footer-col">
      <div class="footer-role">Дизайнер</div>
      <div class="footer-person">Топоева Елена</div>
    </div>
    <div class="footer-col">
      <div class="footer-role">Frontend</div>
      <div class="footer-person">Амелина Кристина</div>
      <div class="footer-person">Бакулин Александр</div>
    </div>
    <div class="footer-col">
      <div class="footer-role">Backend</div>
      <div class="footer-person">Нечаев Андрей</div>
      <div class="footer-person">Миронова Анастасия</div>
    </div>
  </footer>
</template>

<style scoped>
.site-footer {
  margin-top: 40px;
  padding: 28px 32px;
  background: #ffffff;
  border: 1px solid #fee2e2;
  border-radius: 12px;
  box-shadow: 0 2px 4px rgba(0, 0, 0, .03);
  display: grid;
  grid-template-columns: 1.4fr 1fr 1fr 1fr;
  gap: 32px;
  color: var(--text);
  font-size: 14px;
}
.footer-col { min-width: 0; }
.footer-col-about { padding-right: 20px; border-right: 1px solid #F1F1F1; display: flex; align-items: center; }
.footer-title { font-size: 15px; font-weight: 600; color: var(--text); line-height: 1.4; }
.footer-role {
  font-size: 11px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: var(--primary);
  margin-bottom: 8px;
}
.footer-person { font-size: 14px; color: var(--text-light); line-height: 1.6; }

@media (max-width: 900px) {
  .site-footer { grid-template-columns: 1fr 1fr; }
  .footer-col-about {
    grid-column: span 2;
    border-right: none;
    border-bottom: 1px solid #F1F1F1;
    padding-bottom: 16px;
    padding-right: 0;
  }
}
@media (max-width: 520px) {
  .site-footer { grid-template-columns: 1fr; padding: 20px; }
  .footer-col-about { grid-column: auto; }
}
</style>
