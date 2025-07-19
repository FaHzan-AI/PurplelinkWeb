-- phpMyAdmin SQL Dump
-- version 5.2.1
-- https://www.phpmyadmin.net/
--
-- Host: 127.0.0.1
-- Waktu pembuatan: 16 Jul 2025 pada 12.44
-- Versi server: 10.4.28-MariaDB
-- Versi PHP: 8.2.4

SET SQL_MODE = "NO_AUTO_VALUE_ON_ZERO";
START TRANSACTION;
SET time_zone = "+00:00";


/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!40101 SET NAMES utf8mb4 */;

--
-- Database: `purplelinkdb`
--

-- --------------------------------------------------------

--
-- Struktur dari tabel `chat_read_timestamps`
--

CREATE TABLE `chat_read_timestamps` (
  `id` int(11) NOT NULL,
  `user_id` int(11) NOT NULL,
  `chat_id` int(11) NOT NULL COMMENT 'Bisa user_id untuk private atau group_id untuk grup',
  `chat_type` enum('private','group') NOT NULL,
  `last_read_timestamp` timestamp NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp()
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Dumping data untuk tabel `chat_read_timestamps`
--

INSERT INTO `chat_read_timestamps` (`id`, `user_id`, `chat_id`, `chat_type`, `last_read_timestamp`) VALUES
(170, 11, 12, 'private', '2025-07-16 10:24:20'),
(173, 12, 11, 'private', '2025-07-16 10:27:29'),
(174, 12, 13, 'private', '2025-07-16 08:21:03'),
(175, 12, 5, 'group', '2025-07-16 04:42:38'),
(183, 11, 5, 'group', '2025-07-16 08:27:49'),
(184, 11, 13, 'private', '2025-07-16 08:58:14'),
(190, 13, 5, 'group', '2025-07-16 08:11:39'),
(191, 13, 12, 'private', '2025-07-16 09:54:32'),
(192, 13, 11, 'private', '2025-07-16 09:34:18'),
(239, 11, 6, 'group', '2025-07-16 10:24:34'),
(247, 12, 6, 'group', '2025-07-16 10:27:33'),
(253, 13, 6, 'group', '2025-07-16 10:24:58');

-- --------------------------------------------------------

--
-- Struktur dari tabel `groups`
--

CREATE TABLE `groups` (
  `id` int(11) NOT NULL,
  `name` varchar(255) NOT NULL,
  `creator_id` int(11) NOT NULL,
  `created_at` timestamp NOT NULL DEFAULT current_timestamp()
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Dumping data untuk tabel `groups`
--

INSERT INTO `groups` (`id`, `name`, `creator_id`, `created_at`) VALUES
(6, 'PBL201', 12, '2025-07-16 08:52:27');

-- --------------------------------------------------------

--
-- Struktur dari tabel `group_members`
--

CREATE TABLE `group_members` (
  `id` int(11) NOT NULL,
  `group_id` int(11) NOT NULL,
  `user_id` int(11) NOT NULL,
  `role` enum('creator','admin','member') NOT NULL DEFAULT 'member',
  `joined_at` timestamp NOT NULL DEFAULT current_timestamp()
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Dumping data untuk tabel `group_members`
--

INSERT INTO `group_members` (`id`, `group_id`, `user_id`, `role`, `joined_at`) VALUES
(20, 6, 12, 'creator', '2025-07-16 09:25:27'),
(21, 6, 11, 'member', '2025-07-16 09:26:24');

-- --------------------------------------------------------

--
-- Struktur dari tabel `messages`
--

CREATE TABLE `messages` (
  `id` int(11) NOT NULL,
  `user_id` int(11) NOT NULL,
  `receiver_id` int(11) DEFAULT NULL,
  `group_id` int(11) DEFAULT NULL,
  `message_type` varchar(20) NOT NULL DEFAULT 'text',
  `content` mediumtext DEFAULT NULL,
  `timestamp` timestamp NOT NULL DEFAULT current_timestamp(),
  `reply_to_message_id` int(11) DEFAULT NULL,
  `is_edited` tinyint(1) DEFAULT 0,
  `is_deleted` tinyint(1) DEFAULT 0,
  `deleted_by_user_id_1` int(11) DEFAULT NULL,
  `deleted_by_user_id_2` int(11) DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Dumping data untuk tabel `messages`
--

INSERT INTO `messages` (`id`, `user_id`, `receiver_id`, `group_id`, `message_type`, `content`, `timestamp`, `reply_to_message_id`, `is_edited`, `is_deleted`, `deleted_by_user_id_1`, `deleted_by_user_id_2`) VALUES
(90, 12, 11, NULL, 'text', 'EtZYeGfOWVyVXzoMa+xxy+SrW0Q=', '2025-07-16 08:21:08', NULL, 0, 0, 12, 11),
(91, 11, 13, NULL, 'file', 'ha/rFV0nu4f9+KGP51kYKe4EPeTUzWjbQKPylzABRp4yHjLRVIMgTprtrwvYDgqHmIKcRg==', '2025-07-16 08:22:09', NULL, 0, 0, 11, 13),
(92, 11, 13, NULL, 'text', 'ZdKupkiXpPat3P+hteWMj/OUHYpdIanOEAM=', '2025-07-16 08:22:13', NULL, 0, 0, 11, 13),
(93, 11, 13, NULL, 'text', 'ABXxs3DLZeS+Y5V48FkiWu4KCX5yGDBEzw==', '2025-07-16 08:22:29', 91, 0, 0, 11, 13),
(94, 11, 13, NULL, 'text', 'EyiLrFeOsJH/aBm4Y0AbytZLxsf3sZ6R', '2025-07-16 08:22:38', NULL, 0, 0, 11, 13),
(95, 11, 13, NULL, 'text', 'Pesan ini telah dihapus', '2025-07-16 08:22:42', 94, 0, 1, 11, 13),
(96, 11, 12, NULL, 'text', 'QgBocB2LoA19c2RfOa95H4U=', '2025-07-16 08:27:26', NULL, 0, 0, 11, 12),
(97, 11, 12, NULL, 'text', 'Pesan ini telah dihapus', '2025-07-16 08:27:31', 96, 0, 1, 11, 12),
(98, 11, 12, NULL, 'text', 'zk5K9kElx/l8iIcn5lauBLv8', '2025-07-16 08:57:57', NULL, 0, 0, 11, 12),
(99, 11, 12, NULL, 'text', 'wGRzcDdMzUe4vBvJzpR4Dz4fTR5M6o2SwhLAMbvkQcXzFPCGogt4', '2025-07-16 08:58:01', 98, 0, 1, 11, 12),
(100, 11, 12, NULL, 'text', 'wcygn16EqgnMqei2nHQm95uOrhDD', '2025-07-16 09:55:28', NULL, 0, 0, 11, NULL),
(101, 11, 12, NULL, 'file', 'UI1UVtunxR0wFMEwl2YGUjAG3x/K0psHLp9KKmI1Ow/kae7ON8EN', '2025-07-16 09:55:50', NULL, 0, 1, 11, NULL),
(102, 11, 12, NULL, 'text', 'NEklyo4v6Qn79A0HxsdYL5rdu3Ez5VJ7QwplYkvRPSc5+PFkkPjE', '2025-07-16 09:55:59', 101, 0, 1, 11, NULL),
(103, 11, 12, NULL, 'text', 'Bjv/RXgjhXy5ByOz+CdhBmRKfwg=', '2025-07-16 10:04:09', NULL, 0, 0, 11, NULL),
(104, 11, 12, NULL, 'text', '6rwK9NJiaFK08SsS7mGgUOe6DtQ=', '2025-07-16 10:04:16', 103, 0, 0, 11, NULL),
(105, 11, 12, NULL, 'file', '+XdUigClTPOvJRuZ2Br86F0WcMwKCv5b+p/mV2SuYr5RPX8yWKBU', '2025-07-16 10:04:26', NULL, 0, 1, 11, NULL),
(106, 11, 12, NULL, 'text', '0io2odGz9C8q85j1qLZYTyPE8PlvxP24Uf3+8IqpWyTUTueV2KRo', '2025-07-16 10:04:32', 105, 0, 1, 11, NULL),
(107, 11, 12, NULL, 'file', '5t+VTzk2sNbzEvl1n0Ey2mUNaL3eOOg4KdpG', '2025-07-16 10:05:45', NULL, 0, 0, 11, NULL),
(108, 11, 12, NULL, 'text', 'C/RV4fqlVwYyhZdyPqHBfy+NEGAXysb9hFGasSnCejTFSYOKdHZv', '2025-07-16 10:05:49', 107, 0, 1, 11, NULL),
(109, 11, 12, NULL, 'text', '3IgBd4IkP+7rv8XtjwkaVMMrBSQd', '2025-07-16 10:20:14', NULL, 0, 0, 11, NULL),
(110, 11, 12, NULL, 'text', 'ALIToYMgZymCkUyv0H5CYv7pyOXzmlCQiL8i2ENSPfkd7JtQGyR8', '2025-07-16 10:20:18', 109, 0, 1, 11, NULL),
(111, 12, 11, NULL, 'text', 'YDuKzPOorPDJs/YA8HkYMYmLIYKH', '2025-07-16 10:26:32', 107, 0, 0, NULL, NULL);

-- --------------------------------------------------------

--
-- Struktur dari tabel `users`
--

CREATE TABLE `users` (
  `id` int(11) NOT NULL,
  `username` varchar(100) NOT NULL,
  `password` varchar(255) NOT NULL,
  `created_at` timestamp NOT NULL DEFAULT current_timestamp()
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Dumping data untuk tabel `users`
--

INSERT INTO `users` (`id`, `username`, `password`, `created_at`) VALUES
(11, 'hafidz', '$2b$12$6xKGMyYFJcS8QfHT5b.zheQklWT7wZHs5juHSHVcau8MRlCb/amDS', '2025-07-16 03:35:49'),
(12, 'admin', '$2b$12$Q3MwlJrrxL3Al50TCI37N.OvDpjH173ndt7hcrPTMtLriVMUxlptm', '2025-07-16 03:36:04'),
(13, 'ojan', '$2b$12$DEurqtbuEd/F.BJL7kfD5uWqxw5iNxOnvqXE65z84C8xbltdOZ0O.', '2025-07-16 04:37:58');

--
-- Indexes for dumped tables
--

--
-- Indeks untuk tabel `chat_read_timestamps`
--
ALTER TABLE `chat_read_timestamps`
  ADD PRIMARY KEY (`id`),
  ADD UNIQUE KEY `user_chat_unique` (`user_id`,`chat_id`,`chat_type`);

--
-- Indeks untuk tabel `groups`
--
ALTER TABLE `groups`
  ADD PRIMARY KEY (`id`),
  ADD KEY `creator_id` (`creator_id`);

--
-- Indeks untuk tabel `group_members`
--
ALTER TABLE `group_members`
  ADD PRIMARY KEY (`id`),
  ADD UNIQUE KEY `group_user_unique` (`group_id`,`user_id`),
  ADD KEY `user_id` (`user_id`);

--
-- Indeks untuk tabel `messages`
--
ALTER TABLE `messages`
  ADD PRIMARY KEY (`id`),
  ADD KEY `user_id` (`user_id`),
  ADD KEY `receiver_id` (`receiver_id`),
  ADD KEY `group_id` (`group_id`),
  ADD KEY `reply_to_message_id` (`reply_to_message_id`);

--
-- Indeks untuk tabel `users`
--
ALTER TABLE `users`
  ADD PRIMARY KEY (`id`),
  ADD UNIQUE KEY `username` (`username`);

--
-- AUTO_INCREMENT untuk tabel yang dibuang
--

--
-- AUTO_INCREMENT untuk tabel `chat_read_timestamps`
--
ALTER TABLE `chat_read_timestamps`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=292;

--
-- AUTO_INCREMENT untuk tabel `groups`
--
ALTER TABLE `groups`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=7;

--
-- AUTO_INCREMENT untuk tabel `group_members`
--
ALTER TABLE `group_members`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=22;

--
-- AUTO_INCREMENT untuk tabel `messages`
--
ALTER TABLE `messages`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=112;

--
-- AUTO_INCREMENT untuk tabel `users`
--
ALTER TABLE `users`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=14;

--
-- Ketidakleluasaan untuk tabel pelimpahan (Dumped Tables)
--

--
-- Ketidakleluasaan untuk tabel `chat_read_timestamps`
--
ALTER TABLE `chat_read_timestamps`
  ADD CONSTRAINT `chat_read_timestamps_ibfk_1` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE;

--
-- Ketidakleluasaan untuk tabel `groups`
--
ALTER TABLE `groups`
  ADD CONSTRAINT `groups_ibfk_1` FOREIGN KEY (`creator_id`) REFERENCES `users` (`id`) ON DELETE CASCADE;

--
-- Ketidakleluasaan untuk tabel `group_members`
--
ALTER TABLE `group_members`
  ADD CONSTRAINT `group_members_ibfk_1` FOREIGN KEY (`group_id`) REFERENCES `groups` (`id`) ON DELETE CASCADE,
  ADD CONSTRAINT `group_members_ibfk_2` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE;

--
-- Ketidakleluasaan untuk tabel `messages`
--
ALTER TABLE `messages`
  ADD CONSTRAINT `messages_ibfk_1` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE,
  ADD CONSTRAINT `messages_ibfk_2` FOREIGN KEY (`receiver_id`) REFERENCES `users` (`id`) ON DELETE SET NULL,
  ADD CONSTRAINT `messages_ibfk_3` FOREIGN KEY (`group_id`) REFERENCES `groups` (`id`) ON DELETE CASCADE,
  ADD CONSTRAINT `messages_ibfk_4` FOREIGN KEY (`reply_to_message_id`) REFERENCES `messages` (`id`) ON DELETE SET NULL;
COMMIT;

/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
