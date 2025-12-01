# 🎯 Sistema Multi-Comando e Salvamento - Guia Completo

## 📋 Visão Geral

O Blueprint Editor agora possui um sistema completo de **múltiplos comandos** e **salvamento automático**, permitindo criar plugins complexos com organização profissional.

---

## 🗂️ Sistema de Múltiplos Comandos

### Funcionalidades

#### **Criação de Comandos**
- Clique no botão **"+"** na toolbar
- Digite o nome do comando (ex: `hello`, `points`, `duel`)
- Cada comando tem seu próprio grafo independente
- Nome deve usar apenas letras, números e underscore

#### **Gerenciamento de Abas**
- Cada comando aparece como uma aba na toolbar
- **Aba ativa** destacada em azul
- Clique na aba para trocar de comando
- Ícone **"⋮"** para opções (renomear, deletar)

#### **Operações**
1. **Adicionar Comando**: Botão "+" na toolbar
2. **Trocar de Comando**: Clique na aba desejada
3. **Renomear**: Menu "⋮" → Renomear
4. **Deletar**: Menu "⋮" → Deletar (mínimo 1 comando)

---

## 💾 Sistema de Salvamento

### Salvamento Automático (Auto-Save)

O editor salva automaticamente seu progresso:

#### **Quando o Auto-Save Acontece:**
- ✅ A cada **30 segundos** (timer automático)
- ✅ Ao **trocar de comando** (aba)
- ✅ Ao **criar conexão** entre nodes
- ✅ Ao **deletar node**
- ✅ Ao **editar propriedades** de nodes (1 segundo após mudança)
- ✅ Ao **criar/deletar comando**

#### **Onde é Salvo:**
- **localStorage** do navegador
- Não precisa de servidor ou internet
- Dados persistem mesmo fechando o navegador
- Cada projeto é identificado por nome único

---

## 🎮 Botões da Toolbar

### 💾 **Salvar**
- Salva projeto atual no localStorage
- Pede nome do projeto
- Atualiza nome do plugin

### 📂 **Carregar**
- Abre modal com projetos salvos
- Mostra nome, quantidade de comandos e data
- Clique em "Carregar" para abrir
- Botão 🗑️ para deletar projeto

### ⬇️ **Exportar**
- Salva projeto como arquivo `.json`
- Pode ser compartilhado ou guardado externamente
- Backup permanente fora do navegador

### ⬆️ **Importar**
- Carrega projeto de arquivo `.json`
- Útil para restaurar backups
- Importa e salva automaticamente no localStorage

### ✅ **Validar**
- Valida **todos os comandos** do projeto
- Mostra erros de cada comando separadamente
- Verifica antes de compilar

### ⚙️ **Compilar Plugin**
- Compila **todos os comandos** em um único arquivo `.py`
- Gera plugin completo e funcional
- Download automático do arquivo Python
- Mostra quantidade de comandos compilados

---

## 📊 Estrutura de Dados

### Formato do Projeto Salvo

```json
{
  "pluginName": "MeuPlugin",
  "pluginVersion": "1.0.0",
  "pluginAuthor": "Autor",
  "commands": {
    "hello": {
      "nodes": [...],
      "connections": [...]
    },
    "points": {
      "nodes": [...],
      "connections": [...]
    }
  },
  "activeCommand": "hello",
  "timestamp": "2025-11-17T..."
}
```

---

## 🔄 Fluxo de Trabalho Típico

### 1. **Criar Novo Projeto**
```
1. Abrir editor
2. Sistema carrega último projeto automaticamente
3. Ou clicar "Carregar" para escolher projeto
4. Ou começar do zero (comando "hello" criado automaticamente)
```

### 2. **Adicionar Comandos**
```
1. Clicar "+" na toolbar
2. Digitar nome: "points"
3. Construir lógica com nodes
4. Clicar "+" novamente
5. Digitar nome: "duel"
6. Construir lógica com nodes
```

### 3. **Trabalhar com Comandos**
```
1. Trocar entre abas conforme necessário
2. Auto-save cuida do salvamento
3. Editar propriedades de nodes
4. Conectar lógica complexa
```

### 4. **Salvar e Compilar**
```
1. Clicar "Salvar" para dar nome ao projeto
2. Ou deixar auto-save fazer o trabalho
3. Clicar "Validar" para verificar erros
4. Clicar "Compilar Plugin" para gerar .py
5. Arquivo baixado automaticamente
```

---

## 💡 Dicas e Boas Práticas

### ✅ Organização

1. **Nome de Comandos Claros**
   - Use nomes descritivos: `hello`, `duel`, `leaderboard`
   - Evite: `cmd1`, `test`, `asdf`

2. **Um Comando por Funcionalidade**
   - `!hello` → comando "hello"
   - `!points add` → comando "points_add"
   - `!duel start` → comando "duel_start"

3. **Agrupe Funcionalidades Relacionadas**
   - Sistema de duelos: `duel_start`, `duel_accept`, `duel_cancel`
   - Sistema de pontos: `points_get`, `points_add`, `points_remove`

### 🔒 Segurança dos Dados

1. **Backup Regular**
   - Use "Exportar" semanalmente
   - Guarde arquivos `.json` em local seguro
   - localStorage pode ser limpo pelo navegador

2. **Múltiplos Projetos**
   - Salve versões: `MeuPlugin_v1`, `MeuPlugin_v2`
   - Experimente sem medo
   - Sempre pode voltar à versão anterior

3. **Limitações do localStorage**
   - Limite de ~5-10MB por domínio
   - Projetos muito grandes: use Exportar/Importar
   - Limpar cache do navegador = perder dados

### ⚡ Performance

1. **Muitos Comandos**
   - Sistema suporta dezenas de comandos
   - Auto-save leve e rápido
   - Troca de comando instantânea

2. **Grafos Complexos**
   - Sem limite de nodes por comando
   - Conexões ilimitadas
   - Use sub-comandos para organizar

---

## 🎯 Exemplos de Uso

### Plugin de Economia
```
Comandos:
- points → Ver pontos
- points_add → Adicionar pontos (mod only)
- points_remove → Remover pontos (mod only)
- shop → Ver loja
- buy → Comprar item
- inventory → Ver inventário
```

### Plugin de Minigames
```
Comandos:
- duel → Desafiar usuário
- accept → Aceitar duelo
- rps → Pedra, papel, tesoura
- coinflip → Cara ou coroa
- dice → Rolar dado
```

### Plugin de Moderação
```
Comandos:
- timeout → Silenciar usuário
- ban → Banir usuário
- warn → Avisar usuário
- clear → Limpar chat
```

---

## 🐛 Solução de Problemas

### Projeto não carrega ao abrir editor
- Verifique console do navegador (F12)
- Tente "Carregar" manualmente
- localStorage pode ter sido limpo

### Auto-save não funciona
- Verifique console (F12)
- Espaço no localStorage cheio?
- Exporte projeto como backup

### Perdeu trabalho não salvo
- Auto-save salva a cada 30s
- Perda máxima: últimos 30 segundos
- Use "Salvar" antes de tarefas importantes

### Compilação falha
- Use "Validar" primeiro
- Verifique erros em cada comando
- Todo comando precisa de "event_start"

---

## 📈 Estatísticas do Sistema

- **Auto-save**: A cada 30 segundos
- **Comandos**: Ilimitados
- **Nodes por comando**: Ilimitados
- **Projetos salvos**: ~50-100 (depende do tamanho)
- **Tamanho médio**: 10-50KB por projeto
- **Backup externo**: Recomendado semanalmente

---

## 🚀 Próximos Passos

Com este sistema, você pode:

1. ✅ Criar plugins complexos com múltiplos comandos
2. ✅ Trabalhar sem medo de perder progresso
3. ✅ Organizar lógica em comandos separados
4. ✅ Compartilhar projetos via arquivos JSON
5. ✅ Compilar tudo em um único plugin Python

**O Blueprint Editor agora é tão completo quanto programar direto em Python!** 🎉
