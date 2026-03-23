# Contributing to Uppa! 🦦

First off, thank you for considering contributing to Uppa! It's people like you that make Uppa a great productivity tool for everyone.

## 🛠️ Como Contribuir (How to Contribute)

We welcome contributions of all kinds! Whether you're fixing a bug, adding a new feature, or improving documentation. 

### 1. Preparando o Ambiente (Setup)
1. Faça o **Fork** deste repositório.
2. Clone-o para sua máquina local:
   ```bash
   git clone https://github.com/SEU-USUARIO/Uppa-Seu-mascote-de-Produtividade.git
   ```
3. Crie um ambiente virtual e instale as dependências:
   ```bash
   python -m venv venv
   source venv/bin/activate  # ou venv\Scripts\activate no Windows
   pip install -r requirements.txt
   pip install pytest pytest-mock
   ```

### 2. Padrões de Código (Code Standards)
- **Framework Opcional**: O projeto utiliza `CustomTkinter` como base de interface de usuário.
- **Testes**: Somos orientados a testes (TDD). Para qualquer nova funcionalidade na camada de dados (`database.py`) ou regras de negócio, garanta que existam testes unitários correspondentes na pasta `tests/`.

### 3. Rodando os Testes (Running Tests)
Antes de commitar, certifique-se de que nada foi quebrado:
```bash
pytest tests/
```
*(Opcional) Teste a build local rodando `BUILD.bat` no Windows.*

### 4. Submetendo suas mudanças (Pull Requests)
1. Crie uma branch detalhando a feature: `git checkout -b feature/minha-nova-funcionalidade`
2. Commite suas alterações com descrições claras: `git commit -m "feat: Adiciona nova poção à loja"`
3. Push para a branch: `git push origin feature/minha-nova-funcionalidade`
4. Abra um Pull Request e aguarde o review da core team! 💜

## 🐞 Reportando Bugs ou Sugerindo Ideias
Caso encontre algum erro ou tenha uma ideia mágica para a lontra, use a aba **Issues** do Github usando o nosso template oficial (`TEMPLATE_FEEDBACK.md`).

Feliz Codificação e muito foco! 🍅✨
