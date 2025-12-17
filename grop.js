import * as readline from 'node:readline/promises';
import { stdin as input, stdout as output } from 'node:process';

async function main() {
    // Створюємо інтерфейс для введення/виведення
    const rl = readline.createInterface({ input, output });

    const nums: number[] = [];

    while (true) {
        // Запитуємо число у користувача
        const answer = await rl.question("Enter number (0 to stop): ");
        const a: number = Number(answer);

        // Перевірка на вихід
        if (a === 0) {
            break;
        }

        // Перевірка, чи ввів користувач саме число (не текст)
        if (isNaN(a)) {
            console.log("Це не число, спробуйте ще раз.");
            continue;
        }

        nums.push(a);
    }

    // Рахуємо суму
    let sum: number = 0;
    nums.forEach(n => {
        sum = sum + n;
    });

    console.log(`\nВведені числа: ${nums}`);
    console.log(`Сума: ${sum}`);

    // Закриваємо інтерфейс зчитування
    rl.close();
}

// Запуск головної функції
main();
