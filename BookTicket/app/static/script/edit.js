document.addEventListener("DOMContentLoaded", function () {
    // Logic cho "Điểm đi" và "Điểm đến"
    const departureSelect = document.getElementById('departure');
    const destinationSelect = document.getElementById('destination');

    if (departureSelect && destinationSelect) {
        function updateOptions() {
            const departureValue = departureSelect.value;
            const destinationValue = destinationSelect.value;

            // Hiện tất cả các tùy chọn trước khi áp dụng ẩn
            for (let option of departureSelect.options) {
                option.style.display = 'block';
            }
            for (let option of destinationSelect.options) {
                option.style.display = 'block';
            }

            // Ẩn lựa chọn "Điểm đến" ở "Điểm đi" và ngược lại
            if (departureValue) {
                for (let option of destinationSelect.options) {
                    if (option.value === departureValue) {
                        option.style.display = 'none';
                    }
                }
            }

            if (destinationValue) {
                for (let option of departureSelect.options) {
                    if (option.value === destinationValue) {
                        option.style.display = 'none';
                    }
                }
            }
        }

        departureSelect.addEventListener('change', updateOptions);
        destinationSelect.addEventListener('change', updateOptions);
        updateOptions();
    }

    // Logic đặt ngày mặc định
    const departureDateInput = document.getElementById('departure_date');
    if (departureDateInput) {
        const today = new Date();
        const yyyy = today.getFullYear();
        const mm = String(today.getMonth() + 1).padStart(2, '0');
        const dd = String(today.getDate()).padStart(2, '0');

        departureDateInput.value = `${yyyy}-${mm}-${dd}`;
    }


     //Logic hiệu ứng thông báo
    const alerts = document.querySelectorAll('.alert');
    if (alerts.length > 0) {
        alerts.forEach(alert => {
            alert.classList.add('fade-in');

            // Tự động ẩn sau 3 giây
            setTimeout(() => {
                alert.classList.remove('fade-in');
                alert.classList.add('fade-out');
                setTimeout(() => alert.remove(), 500);
            }, 3000);
        });
    }
})











