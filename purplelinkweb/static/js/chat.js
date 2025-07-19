document.addEventListener('DOMContentLoaded', () => {
    // === Inisialisasi Dasar ===
    const socket = io();
    const elements = {
        form: document.getElementById('chat-form'),
        input: document.getElementById('message'),
        messages: document.getElementById('messages'),
        userSearchInput: document.getElementById('user-search-input'),
        searchResults: document.getElementById('search-results'),
        groupList: document.getElementById('group-list'),
        privateChatList: document.getElementById('private-chat-list'),
        allUsersList: document.getElementById('all-users-list'),
        chatArea: document.getElementById('chat-area'),
        welcomeMessage: document.getElementById('welcome-message'),
        currentChatNameEl: document.getElementById('current-chat-name'),
        createGroupForm: document.getElementById('create-group-form'),
        addMemberBtn: document.getElementById('add-member-btn'),
        addMemberSearchInput: document.getElementById('add-member-search-input'),
        addMemberSearchResults: document.getElementById('add-member-search-results'),
        attachFileBtn: document.getElementById('attach-file-button'),
        emojiBtn: document.getElementById('emoji-button'),
        emojiMenu: document.getElementById('emoji-menu'),
        replyPreview: document.getElementById('reply-preview'),
        replyPreviewUser: document.getElementById('reply-preview-user'),
        replyPreviewText: document.getElementById('reply-preview-text'),
        cancelReplyBtn: document.getElementById('cancel-reply-btn'),
        groupMembersList: document.getElementById('group-members-list'),
        clearHistoryBtn: document.getElementById('clear-history-btn'),
        sidebarContainer: document.getElementById('sidebar-container'),
        toggleBtn: document.getElementById('sidebar-toggle-btn'),
        chatHeader: document.getElementById('chat-header'),
    };
    let currentChat = null;
    let replyToMessage = null;
    let searchTimeout = null;
    let onlineUsers = new Set();
    let members = [];
    let currentUserRole = 'member';
    const fileInput = document.createElement('input');
    fileInput.type = 'file';
    fileInput.style.display = 'none';
    document.body.appendChild(fileInput);

    // === Fungsi Bantuan ===
    async function apiCall(url, options = {}) {
        try {
            const response = await fetch(url, options);
            if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
            return await response.json();
        } catch (error) {
            console.error(`API call failed for ${url}:`, error);
            return null;
        }
    }

    function formatDateSeparator(dateString) {
        const date = new Date(dateString);
        const today = new Date();
        const yesterday = new Date();
        yesterday.setDate(yesterday.getDate() - 1);

        if (date.toDateString() === today.toDateString()) return 'Hari Ini';
        if (date.toDateString() === yesterday.toDateString()) return 'Kemarin';
        return date.toLocaleDateString('id-ID', { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' });
    }

    function updateUserOnlineStatus(userId, status) {
        const isOnline = status === 'online';
        if (isOnline) {
            onlineUsers.add(userId);
        } else {
            onlineUsers.delete(userId);
        }

        const chatItem = document.getElementById(`chat-item-private-${userId}`);
        if (chatItem) {
            let statusIndicator = chatItem.querySelector('.online-indicator');
            if (isOnline && !statusIndicator) {
                statusIndicator = document.createElement('span');
                statusIndicator.className = 'online-indicator';
                const nameSpan = chatItem.querySelector('span');
                nameSpan.insertAdjacentElement('afterend', statusIndicator);
            } else if (!isOnline && statusIndicator) {
                statusIndicator.remove();
            }
        }

        if (currentChat && currentChat.type === 'private' && currentChat.id === userId) {
            const headerStatus = document.getElementById('chat-header-status');
            if(headerStatus) {
                headerStatus.textContent = isOnline ? 'Online' : 'Offline';
                headerStatus.style.color = isOnline ? 'green' : 'grey';
            }
        }
    }

    // === Logika UI ===
    const UILogic = {
        renderMessage: (data) => {
            // --- PERBAIKAN UTAMA: DIMULAI DARI SINI ---
            // Jika pesan sudah dihapus, langsung tampilkan bubble "telah dihapus"
            // dan hentikan proses render selanjutnya.
            if (data.is_deleted) {
                return `<div class="message-body"><p class="text-muted fst-italic">Pesan ini telah dihapus</p></div>`;
            }
            // --- AKHIR DARI PERBAIKAN ---

            // Jika pesan tidak dihapus, logika di bawah ini berjalan seperti biasa.
            const senderLabelHTML = data.user_id === USER_ID ? '' : `<strong>${data.sender_username}</strong>`;
            let replyHTML = '';
            if (data.reply_to_message_id && data.replied_content) {
                replyHTML = `<div class="reply-context"><strong>${data.replied_username || '...'}</strong><p>${data.replied_content}</p></div>`;
            }
            
            let messageContentHTML = '';
            if (data.message_type === 'file') {
                const filePath = data.group_id ? `group_${data.group_id}/${data.content}` : `${data.user_id}/${data.content}`;
                const fileUrl = `/files/${filePath}`;
                const fileName = data.content;
                const fileExtension = fileName.split('.').pop().toLowerCase();
                let fileDisplayHTML = '';
                if (['jpg', 'jpeg', 'png', 'gif', 'bmp', 'webp'].includes(fileExtension)) {
                    fileDisplayHTML = `<a href="${fileUrl}" target="_blank" download><img src="${fileUrl}" class="image-preview" alt="${fileName}"></a>`;
                } else {
                    let iconClass = 'fa-solid fa-file';
                    switch (fileExtension) {
                        case 'pdf': iconClass = 'fa-solid fa-file-pdf'; break;
                        case 'doc': case 'docx': iconClass = 'fa-solid fa-file-word'; break;
                        case 'xls': case 'xlsx': iconClass = 'fa-solid fa-file-excel'; break;
                        case 'zip': case 'rar': iconClass = 'fa-solid fa-file-zipper'; break;
                        case 'ppt': case 'pptx': iconClass = 'fa-solid fa-file-powerpoint'; break;
                    }
                    fileDisplayHTML = `<div class="file-message-container"><i class="${iconClass} file-icon"></i><a href="${fileUrl}" target="_blank" download>${fileName}</a></div>`;
                }
                messageContentHTML = fileDisplayHTML;
            } else {
                messageContentHTML = `<p>${data.content}</p>`;
            }
            
            const editedMarker = data.is_edited ? '<span class="edited-marker">(diedit)</span>' : '';
            let optionsHTML = '';
            optionsHTML += `<span class="message-options-btn" data-message-id="${data.id}">...</span><div class="options-menu" id="options-menu-${data.id}">`;
            optionsHTML += `<a href="#" class="reply-btn">Balas</a>`;
            if (data.user_id === USER_ID) {
                optionsHTML += `<a href="#" class="edit-btn">Edit</a><a href="#" class="delete-btn">Hapus</a>`;
            }
            optionsHTML += `</div>`;
            
            const timestamp = new Date(data.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
            return `${optionsHTML}${senderLabelHTML}${replyHTML}
                <div class="message-body">
                    ${messageContentHTML}
                    <div class="message-meta">
                        <small class="text-muted">${timestamp}</small>
                        ${editedMarker}
                    </div>
                </div>`;
        },
        appendMessage: (data) => {
            const isScrolledToBottom = elements.messages.scrollHeight - elements.messages.clientHeight <= elements.messages.scrollTop + 1;

            if (data.type === 'date_separator' || data.type === 'unread_separator') {
                const separator = document.createElement('div');
                separator.className = 'chat-separator';
                if (data.type === 'date_separator') {
                    separator.innerHTML = `<span>${formatDateSeparator(data.date)}</span>`;
                } else {
                    separator.innerHTML = `<span>Pesan belum dibaca</span>`;
                    separator.classList.add('unread-marker');
                }
                elements.messages.appendChild(separator);
                return;
            }

            const bubble = document.createElement('div');
            bubble.id = `message-${data.id}`;
            bubble.className = `message-bubble ${data.user_id === USER_ID ? 'sent' : 'received'}`;
            bubble.innerHTML = UILogic.renderMessage(data);
            elements.messages.appendChild(bubble);

            if (isScrolledToBottom) {
                elements.messages.scrollTop = elements.messages.scrollHeight;
            }
        },
        createChatItem: (name, type, data, unreadCount = 0) => {
            const item = document.createElement('a');
            item.href = '#';
            item.className = 'list-group-item list-group-item-action d-flex justify-content-between align-items-center';
            item.id = `chat-item-${type}-${data.id}`;
            const nameSpan = document.createElement('span');
            nameSpan.textContent = name;
            item.appendChild(nameSpan);

            if (type === 'private' && onlineUsers.has(data.id)) {
                const statusIndicator = document.createElement('span');
                statusIndicator.className = 'online-indicator';
                nameSpan.insertAdjacentElement('afterend', statusIndicator);
            }

            if (unreadCount > 0) {
                const badge = document.createElement('span');
                badge.className = 'badge bg-danger rounded-pill';
                badge.textContent = unreadCount;
                item.appendChild(badge);
            }
            item.onclick = (e) => {
                e.preventDefault();
                Chat.start({ type, id: data.id, name, creator_id: data.creator_id });
            };
            return item;
        },
        prependGroup: (group) => {
            const groupItem = UILogic.createChatItem(group.name, 'group', group);
            elements.groupList.prepend(groupItem);
        },
        updateMemberList: (membersData) => {
            members = membersData;
            const self = members.find(m => m.id === USER_ID);
            currentUserRole = self ? self.role : 'member';

            members.sort((a, b) => {
                const roles = { creator: 0, admin: 1, member: 2 };
                return roles[a.role] - roles[b.role];
            });

            const memberDisplayString = members.map(member => {
                let roleBadge = '';
                if (member.role === 'creator') roleBadge = ' (Creator)';
                else if (member.role === 'admin') roleBadge = ' (Admin)';
                return `${member.username}${roleBadge}`;
            }).join(', ');
            
            elements.groupMembersList.textContent = memberDisplayString;
        }
    };

    // === Logika Chat ===
    const Chat = {
        start: async (chatInfo) => {
            currentChat = chatInfo;
            elements.chatArea.style.display = 'flex';
            elements.welcomeMessage.style.display = 'none';
            elements.currentChatNameEl.textContent = chatInfo.name;
            elements.messages.innerHTML = 'Memuat riwayat...';
            
            // Perbaikan: Tampilkan selalu tombol hapus riwayat
            elements.clearHistoryBtn.style.display = 'block';

            const headerStatus = document.getElementById('chat-header-status');
            elements.groupMembersList.textContent = ''; 

            // Hapus tombol keluar grup lama sebelum menambahkan yang baru
            elements.chatHeader.querySelector('#leave-group-btn')?.remove();

            let historyUrl;
            if (chatInfo.type === 'private') {
                elements.addMemberBtn.style.display = 'none';
                const isOnline = onlineUsers.has(chatInfo.id);
                headerStatus.textContent = isOnline ? 'Online' : 'Offline';
                headerStatus.style.color = isOnline ? 'green' : 'grey';
                historyUrl = `/chat/history?receiver_id=${chatInfo.id}`;
            } else {
                headerStatus.textContent = '';
                const leaveBtn = document.createElement('button');
                leaveBtn.id = 'leave-group-btn';
                leaveBtn.className = 'btn btn-sm btn-warning';
                leaveBtn.title = 'Keluar dari Grup';
                leaveBtn.innerHTML = '<i class="fa-solid fa-arrow-right-from-bracket"></i>';
                elements.chatHeader.querySelector('.d-flex.gap-2').appendChild(leaveBtn);
                historyUrl = `/groups/${chatInfo.id}/history`;
            }

            const data = await apiCall(historyUrl);

            elements.messages.innerHTML = '';
            if (data && data.history) {
                data.history.forEach(UILogic.appendMessage);
            }
            if (!elements.messages.innerHTML.trim()) {
                elements.messages.innerHTML = '<p class="text-center text-muted">Belum ada pesan.</p>';
            }
            elements.messages.scrollTop = elements.messages.scrollHeight;
            
            if (chatInfo.type === 'group' && data && data.members) {
                UILogic.updateMemberList(data.members);
                const self = data.members.find(m => m.id === USER_ID);
                if (self && (self.role === 'creator' || self.role === 'admin')) {
                    elements.addMemberBtn.style.display = 'block';
                } else {
                    elements.addMemberBtn.style.display = 'none';
                }
            } else {
                 elements.addMemberBtn.style.display = 'none';
            }

            Chat.cancelReply();
            const chatItem = document.getElementById(`chat-item-${chatInfo.type}-${chatInfo.id}`);
            if (chatItem) chatItem.querySelector('.badge')?.remove();
            apiCall('/chat/mark_as_read', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ chat_id: chatInfo.id, chat_type: chatInfo.type })
            });
        },
        sendMessage: (e) => {
            e.preventDefault();
            const text = elements.input.value.trim();
            if (!text || !currentChat) return;
            const payload = { message: text, reply_to_message_id: replyToMessage ? replyToMessage.id : null };
            const eventName = currentChat.type === 'group' ? 'group_message' : 'chat_message';
            if (currentChat.type === 'group') payload.group_id = currentChat.id;
            else payload.receiver_id = currentChat.id;
            socket.emit(eventName, payload);
            elements.input.value = '';
            Chat.cancelReply();
            elements.input.focus();
        },
        prepareReply: (messageEl) => {
        // Cari elemen-elemen penting di dalam gelembung pesan
        const imagePreviewInBubble = messageEl.querySelector('.image-preview');
        const fileLinkInBubble = messageEl.querySelector('.file-message-container a');
        const textContentInBubble = messageEl.querySelector('.message-body p');

        let replyContentHTML = ''; // Variabel untuk menyimpan HTML pratinjau

        // Prioritaskan untuk mencari pratinjau gambar
        if (imagePreviewInBubble) {
            // Jika pesan berisi gambar, buat tag <img> baru untuk pratinjau balasan
            replyContentHTML = `<img src="${imagePreviewInBubble.src}" class="reply-image-preview" alt="Pratinjau Gambar"> Balasan untuk gambar`;
        } 
        // Jika bukan gambar, cari tautan file lain
        else if (fileLinkInBubble) {
            replyContentHTML = `File: ${fileLinkInBubble.textContent}`;
        } 
        // Jika hanya pesan teks biasa
        else if (textContentInBubble) {
            replyContentHTML = textContentInBubble.textContent;
        }

        // Simpan informasi pesan yang akan dibalas
        replyToMessage = {
            id: messageEl.id.split('-')[1],
            user: messageEl.querySelector('strong')?.textContent || 'Anda',
            text: replyContentHTML
        };

        // Tampilkan pratinjau balasan di UI
        elements.replyPreviewUser.textContent = `Membalas kepada ${replyToMessage.user}`;
        elements.replyPreviewText.innerHTML = replyToMessage.text;
        elements.replyPreview.style.display = 'block';
        elements.input.focus();
        },
        cancelReply: () => {
            replyToMessage = null;
            elements.replyPreview.style.display = 'none';
        },
        sendFile: async () => {
            if (!fileInput.files.length || !currentChat) return;
            const file = fileInput.files[0];
            const formData = new FormData();
            formData.append('file', file);

            let url = '';
            if (currentChat.type === 'group') {
                url = `/files/upload/group/${currentChat.id}`;
            } else {
                url = '/files/upload/private';
                formData.append('receiver_id', currentChat.id);
            }

            try {
                const response = await fetch(url, { method: 'POST', body: formData });
                const data = await response.json();
                
                if (response.ok && data.status === true) {
                    socket.emit('broadcast_file_message', { message: data.message });
                } else {
                    alert(data.error || 'Gagal mengunggah file.');
                }

            } catch (error) {
                console.error('File upload error:', error);
                alert('Terjadi kesalahan saat mengunggah file.');
            } finally {
                fileInput.value = '';
            }
        }
    };

    async function loadAndDisplayChats() {
        try {
            const [groupsData, privateChatsData, unreadCounts, allUsersData] = await Promise.all([
                apiCall('/groups'),
                apiCall('/chat/private_chats'),
                apiCall('/chat/unread_counts'),
                apiCall('/users/all')
            ]);

            elements.groupList.innerHTML = '';
            if (groupsData && groupsData.groups) {
                groupsData.groups.forEach(group => {
                    const count = unreadCounts[`group_${group.id}`] || 0;
                    elements.groupList.appendChild(UILogic.createChatItem(group.name, 'group', group, count));
                });
            }

            elements.privateChatList.innerHTML = '';
            if (privateChatsData && privateChatsData.private_chats) {
                privateChatsData.private_chats.forEach(chat => {
                    const count = unreadCounts[`private_${chat.id}`] || 0;
                    elements.privateChatList.appendChild(UILogic.createChatItem(chat.username, 'private', chat, count));
                });
            }

            elements.allUsersList.innerHTML = '';
            if (allUsersData && allUsersData.users) {
                allUsersData.users.forEach(user => {
                    const item = UILogic.createChatItem(user.username, 'private', user);
                    item.onclick = (ev) => {
                        ev.preventDefault();
                        if (!document.getElementById(`chat-item-private-${user.id}`)) {
                            elements.privateChatList.prepend(UILogic.createChatItem(user.username, 'private', user));
                        }
                        Chat.start({ type: 'private', id: user.id, name: user.username });
                    };
                    elements.allUsersList.appendChild(item);
                });
            }
        } catch (error) {
            console.error("Gagal memuat daftar chat:", error);
        }
    }

    function updateNotificationBadge(type, id) {
        const chatItem = document.getElementById(`chat-item-${type}-${id}`);
        if (!chatItem) {
            loadAndDisplayChats(); 
            return;
        }
        let badge = chatItem.querySelector('.badge');
        if (badge) {
            badge.textContent = parseInt(badge.textContent) + 1;
        } else {
            badge = document.createElement('span');
            badge.className = 'badge bg-danger rounded-pill';
            badge.textContent = '1';
            chatItem.appendChild(badge);
        }
    }

    // === Event Delegation & Listeners ===
    elements.messages.addEventListener('click', (e) => {
        const target = e.target;
        document.querySelectorAll('.options-menu').forEach(menu => {
            if (!menu.previousElementSibling.contains(target)) menu.style.display = 'none';
        });

        if (target.classList.contains('message-options-btn')) {
            const menu = target.nextElementSibling;
            menu.style.display = menu.style.display === 'block' ? 'none' : 'block';
            e.stopPropagation();
        }

        const messageBubble = target.closest('.message-bubble');
        if (!messageBubble) return;

        if (target.classList.contains('reply-btn')) {
            e.preventDefault();
            Chat.prepareReply(messageBubble);
            target.closest('.options-menu').style.display = 'none';
        } else if (target.classList.contains('delete-btn')) {
            e.preventDefault();
            if (confirm('Apakah Anda yakin ingin menghapus pesan ini?')) {
                socket.emit('delete_message', { message_id: messageBubble.id.split('-')[1] });
            }
            target.closest('.options-menu').style.display = 'none';
        } else if (target.classList.contains('edit-btn')) {
            e.preventDefault();
            const currentContent = messageBubble.querySelector('.message-body p')?.textContent;
            if (currentContent) {
                const newContent = prompt('Edit pesan Anda:', currentContent);
                if (newContent && newContent.trim() !== '' && newContent.trim() !== currentContent) {
                    socket.emit('edit_message', { message_id: messageBubble.id.split('-')[1], new_content: newContent.trim() });
                }
            }
            target.closest('.options-menu').style.display = 'none';
        }
    });

    elements.clearHistoryBtn.addEventListener('click', () => {
        if (!currentChat) return;
        let confirmText = `Anda yakin ingin menghapus riwayat percakapan dengan ${currentChat.name}?`;
        if (currentChat.type === 'private') {
            confirmText += "\nTindakan ini tidak akan memengaruhi riwayat chat pengguna lain.";
        } else {
            confirmText += "\nTindakan ini akan menghapus riwayat untuk semua anggota grup!";
        }
        if (confirm(confirmText)) {
            socket.emit('clear_history', { chat_id: currentChat.id, chat_type: currentChat.type });
        }
    });

    elements.cancelReplyBtn.addEventListener('click', Chat.cancelReply);
    
    document.addEventListener('click', (e) => {
        if (!e.target.closest('.message-bubble')) {
            document.querySelectorAll('.options-menu').forEach(menu => menu.style.display = 'none');
        }
        if (!elements.emojiBtn.contains(e.target) && !elements.emojiMenu.contains(e.target)) {
            elements.emojiMenu.style.display = 'none';
        }
    });

    elements.form.addEventListener('submit', Chat.sendMessage);
    elements.attachFileBtn.addEventListener('click', () => fileInput.click());
    fileInput.addEventListener('change', Chat.sendFile);

    elements.createGroupForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const nameInput = document.getElementById('group-name-input');
        const name = nameInput.value.trim();
        if (!name) return;
        const data = await apiCall('/groups/create', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ name }) });
        if (data && data.status === 'ok') {
            const modal = bootstrap.Modal.getInstance(document.getElementById('createGroupModal'));
            modal.hide();
            nameInput.value = '';
            UILogic.prependGroup(data.group);
        } else {
            alert(`Gagal membuat grup: ${data ? data.error : 'Kesalahan server'}`);
        }
    });

    elements.addMemberSearchInput.addEventListener('keyup', (e) => {
        clearTimeout(searchTimeout);
        if (!currentChat || currentChat.type !== 'group') return;
        const query = e.target.value.trim();
        if (query.length < 1) {
            elements.addMemberSearchResults.innerHTML = '';
            return;
        }
        searchTimeout = setTimeout(async () => {
            const data = await apiCall(`/groups/${currentChat.id}/non_members?q=${query}`);
            elements.addMemberSearchResults.innerHTML = '';
            if (data && data.users) {
                data.users.forEach(user => {
                    const item = document.createElement('a');
                    item.href = '#';
                    item.className = 'list-group-item list-group-item-action';
                    item.textContent = user.username;
                    item.onclick = (ev) => {
                        ev.preventDefault();
                        socket.emit('add_member_to_group', { user_id: user.id, group_id: currentChat.id });
                    };
                    elements.addMemberSearchResults.appendChild(item);
                });
            }
        }, 300);
    });

    elements.groupMembersList.addEventListener('click', (e) => {
        const target = e.target;
        const memberItem = target.closest('.group-member-item');
        if (!memberItem) return;

        const optionsBtn = memberItem.querySelector('.member-options-btn');
        if (optionsBtn && optionsBtn.contains(target)) {
             e.preventDefault();
            const menu = memberItem.querySelector('.options-menu');
            if(menu) menu.style.display = menu.style.display === 'block' ? 'none' : 'block';
            return;
        }
        
        const memberId = parseInt(memberItem.dataset.userId);

        if (target.classList.contains('promote-admin-btn')) {
            e.preventDefault();
            if(confirm(`Anda yakin ingin menjadikan anggota ini sebagai admin?`)) {
                socket.emit('promote_to_admin', { user_id: memberId, group_id: currentChat.id });
            }
        } else if (target.classList.contains('remove-member-btn')) {
            e.preventDefault();
            if(confirm(`Anda yakin ingin mengeluarkan anggota ini dari grup?`)) {
                socket.emit('remove_from_group', { user_id: memberId, group_id: currentChat.id });
            }
        }
    });

    elements.chatHeader.addEventListener('click', (e) => {
        if (e.target.closest('#leave-group-btn')) {
            if (confirm(`Anda yakin ingin keluar dari grup "${currentChat.name}"?`)) {
                socket.emit('leave_group', { group_id: currentChat.id });
            }
        }
    });
    
    elements.userSearchInput.addEventListener('keyup', (e) => {
        clearTimeout(searchTimeout);
        const query = e.target.value.trim();
        elements.searchResults.style.display = query.length > 0 ? 'block' : 'none';
        elements.allUsersList.style.display = query.length > 0 ? 'none' : 'block';

        if (query.length < 1) {
            elements.searchResults.innerHTML = '';
            return;
        }
        searchTimeout = setTimeout(async () => {
            const data = await apiCall(`/chat/search_user?q=${query}`);
            elements.searchResults.innerHTML = '';
            if (data && data.users) {
                data.users.forEach(user => {
                    const item = UILogic.createChatItem(user.username, 'private', user);
                    item.onclick = (ev) => {
                        ev.preventDefault();
                        if (!document.getElementById(`chat-item-private-${user.id}`)) {
                            elements.privateChatList.prepend(UILogic.createChatItem(user.username, 'private', user));
                        }
                        Chat.start({ type: 'private', id: user.id, name: user.username });
                        elements.userSearchInput.value = '';
                        elements.searchResults.innerHTML = '';
                        elements.searchResults.style.display = 'none';
                        elements.allUsersList.style.display = 'block';
                    };
                    elements.searchResults.appendChild(item);
                });
            }
        }, 300);
    });

    elements.emojiBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        elements.emojiMenu.style.display = elements.emojiMenu.style.display === 'none' ? 'block' : 'none';
    });

    elements.emojiMenu.innerHTML = '';
    const emojis = [
        // Ekspresi wajah
        '😀', '😂', '🤣', '😊', '😍', '😎', '😭', '😡', '🥺', '🤯',
        // Tangan dan gesture
        '👍', '👎', '👏', '🙏', '🤝', '👌', '✌️', '🤙', '👊', '🖐️',
        // Cinta & simbol
        '❤️', '🧡', '💛', '💚', '💙', '💜', '🖤', '💔', '❣️', '💯',
        // Api dan simbol keren
        '🔥', '💥', '⚡', '🌟', '✨', '💫', '🌀', '💢', '💣', '🗿',
        // Makanan
        '🍕', '🍔', '🍟', '🍗', '🍜', '🍩', '🍪', '🍓', '🍉', '🍇',
        // Hewan
        '🐶', '🐱', '🐭', '🐰', '🦊', '🐻', '🐼', '🦁', '🐸', '🐵'
    ];
    emojis.forEach(emojiText => {
        const emojiSpan = document.createElement('span');
        emojiSpan.className = 'emoji';
        emojiSpan.textContent = emojiText;
        emojiSpan.addEventListener('click', () => {
            elements.input.value += emojiText;
            elements.emojiMenu.style.display = 'none';
            elements.input.focus();
        });
        elements.emojiMenu.appendChild(emojiSpan);
    });

    // === Socket.IO Handlers ===
    socket.on('new_message', (data) => {
        const isChatActive = currentChat && currentChat.type === 'private' && (data.user_id === currentChat.id || data.receiver_id === currentChat.id);
        if (isChatActive) {
            const placeholder = elements.messages.querySelector('.text-muted');
            if (placeholder) placeholder.remove();
            UILogic.appendMessage(data);
        } else {
            if (data.user_id !== USER_ID) {
                updateNotificationBadge('private', data.user_id);
            }
        }
    });

    socket.on('new_group_message', (data) => {
        const isChatActive = currentChat && currentChat.type === 'group' && currentChat.id === data.group_id;
        if (isChatActive) {
            const placeholder = elements.messages.querySelector('.text-muted');
            if (placeholder) placeholder.remove();
            UILogic.appendMessage(data);
        } else {
            if (data.user_id !== USER_ID) {
                updateNotificationBadge('group', data.group_id);
            }
        }
    });

    socket.on('message_deleted', (data) => {
        const bubble = document.getElementById(`message-${data.id}`);
        if (bubble) {
            bubble.innerHTML = `<div class="message-body"><p class="text-muted fst-italic">Pesan ini telah dihapus</p></div>`;
        }
    });

    socket.on('message_updated', (data) => {
        const bubble = document.getElementById(`message-${data.id}`);
        if (bubble) {
            bubble.querySelector('.message-body p').textContent = data.content;
            if (!bubble.querySelector('.edited-marker')) {
                const marker = document.createElement('span');
                marker.className = 'edited-marker';
                marker.textContent = ' (diedit)';
                bubble.querySelector('.message-meta .text-muted').insertAdjacentElement('afterend', marker);
            }
        }
    });

    socket.on('added_to_group', (groupData) => {
        alert(`Anda telah ditambahkan ke grup: ${groupData.name}`);
        UILogic.prependGroup(groupData);
    });

    socket.on('add_member_success', () => {
        alert('Anggota berhasil ditambahkan!');
        const modal = bootstrap.Modal.getInstance(document.getElementById('addMemberModal'));
        modal.hide();
        elements.addMemberSearchInput.value = '';
        elements.addMemberSearchResults.innerHTML = '';
    });

    socket.on('add_member_failed', (data) => {
        alert(`Gagal: ${data.error}`);
    });

    socket.on('member_list_changed', async (data) => {
        if (currentChat && currentChat.id === data.group_id) {
            const response = await apiCall(`/groups/${data.group_id}/history`);
            if (response && response.members) {
                UILogic.updateMemberList(response.members);
            }
        }
    });
    
    socket.on('you_were_removed', (data) => {
        alert(`Anda telah dikeluarkan dari grup "${data.group_name}".`);
        const groupItem = document.getElementById(`chat-item-group-${data.group_id}`);
        if(groupItem) groupItem.remove();
        if(currentChat && currentChat.id === data.group_id) {
            elements.chatArea.style.display = 'none';
            elements.welcomeMessage.style.display = 'block';
            currentChat = null;
        }
    });

    socket.on('leave_group_success', (data) => {
        const groupItem = document.getElementById(`chat-item-group-${data.group_id}`);
        if(groupItem) groupItem.remove();
        if(currentChat && currentChat.id === data.group_id) {
            elements.chatArea.style.display = 'none';
            elements.welcomeMessage.style.display = 'block';
            currentChat = null;
        }
        alert('Anda telah keluar dari grup.');
    });

    socket.on('leave_group_failed', (data) => {
        alert(`Gagal keluar dari grup: ${data.error}`);
    });

    socket.on('history_cleared', (data) => {
        if (currentChat && currentChat.type === data.chat_type && currentChat.id == data.chat_id) {
            elements.messages.innerHTML = '<p class="text-center text-muted">Riwayat percakapan telah dihapus.</p>';
        }
    });

    socket.on('online_users_list', (data) => {
        onlineUsers = new Set(data.users);
        loadAndDisplayChats();
    });

    socket.on('user_status_change', (data) => {
        updateUserOnlineStatus(data.user_id, data.status);
    });

    // === Inisialisasi Halaman ===
    loadAndDisplayChats();

    // === Sidebar Navigation Logic ===
    const sidebarLinks = document.querySelectorAll('.sidebar-link');
    const sidebarPanels = document.querySelectorAll('.sidebar-panel');

    sidebarLinks.forEach(link => {
        link.addEventListener('click', (e) => {
            e.preventDefault();
            sidebarLinks.forEach(l => l.classList.remove('active'));
            sidebarPanels.forEach(p => p.classList.remove('active'));
            link.classList.add('active');
            const targetPanelId = link.getAttribute('data-target');
            const targetPanel = document.querySelector(`.sidebar-panel[data-panel="${targetPanelId}"]`);
            if (targetPanel) {
                targetPanel.classList.add('active');
            }
        });
    });

    // ===== Sidebar Collapse/Expand Logic =====
    if (elements.toggleBtn) {
        elements.toggleBtn.addEventListener('click', () => {
            elements.sidebarContainer.classList.toggle('collapsed');
        });
    }

});