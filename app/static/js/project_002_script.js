document.addEventListener("DOMContentLoaded", () => {
  // Set current year in footer
  document.getElementById("current-year").textContent = new Date().getFullYear()

  // Tabs functionality
  setupTabs(".tab-btn", ".tab-pane")
  setupTabs(".tech-tab-btn", ".tech-tab-pane", "tech")
  setupTabs(".automation-tab-btn", ".automation-tab-pane", "automation")

  // Accordion functionality
  setupAccordion()

  // Smooth scrolling for navigation links
  setupSmoothScrolling()

  // Sticky navigation highlighting
  setupScrollSpy()
})

// Tabs functionality
function setupTabs(tabBtnSelector, tabPaneSelector, prefix = "") {
  const tabBtns = document.querySelectorAll(tabBtnSelector)

  tabBtns.forEach((btn) => {
    btn.addEventListener("click", () => {
      // Remove active class from all buttons and panes
      document.querySelectorAll(tabBtnSelector).forEach((b) => b.classList.remove("active"))
      document.querySelectorAll(tabPaneSelector).forEach((p) => p.classList.remove("active"))

      // Add active class to clicked button
      btn.classList.add("active")

      // Get the tab id from data attribute
      const tabId = btn.getAttribute("data-tab")

      // Add active class to corresponding pane
      const paneId = prefix ? `${tabId}-tab` : tabId
      const pane = document.getElementById(paneId)
      if (pane) {
        pane.classList.add("active")
      }
    })
  })
}

// Accordion functionality
function setupAccordion() {
  const accordionItems = document.querySelectorAll(".accordion-item")

  accordionItems.forEach((item) => {
    const header = item.querySelector(".accordion-header")

    header.addEventListener("click", () => {
      // Toggle active class on clicked item
      item.classList.toggle("active")

      // Close other accordion items
      accordionItems.forEach((otherItem) => {
        if (otherItem !== item) {
          otherItem.classList.remove("active")
        }
      })
    })
  })
}

// Smooth scrolling for navigation links
function setupSmoothScrolling() {
  const navLinks = document.querySelectorAll(".nav-links a")

  navLinks.forEach((link) => {
    link.addEventListener("click", function (e) {
      e.preventDefault()

      const targetId = this.getAttribute("href")
      const targetElement = document.querySelector(targetId)

      if (targetElement) {
        const navHeight = document.querySelector(".main-nav").offsetHeight
        const targetPosition = targetElement.getBoundingClientRect().top + window.pageYOffset - navHeight

        window.scrollTo({
          top: targetPosition,
          behavior: "smooth",
        })
      }
    })
  })
}

// Scroll spy for navigation highlighting
function setupScrollSpy() {
  const sections = document.querySelectorAll("section[id]")
  const navLinks = document.querySelectorAll(".nav-links a")

  window.addEventListener("scroll", () => {
    let current = ""
    const navHeight = document.querySelector(".main-nav").offsetHeight

    sections.forEach((section) => {
      const sectionTop = section.offsetTop - navHeight - 100
      const sectionHeight = section.offsetHeight

      if (window.pageYOffset >= sectionTop) {
        current = section.getAttribute("id")
      }
    })

    navLinks.forEach((link) => {
      link.classList.remove("active")
      if (link.getAttribute("href") === `#${current}`) {
        link.classList.add("active")
      }
    })
  })
}
